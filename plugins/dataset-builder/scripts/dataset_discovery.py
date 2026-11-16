#!/usr/bin/env python3
"""
Dataset discovery for dataset-builder plugin.

Provides multiple methods to discover available datasets:
1. Oasis API - Lists datasets registered in Oasis
2. BigQuery - Lists tables in us_east1_devrev
3. Hardcoded fallback - Known stock datasets

Usage:
    # List all stock datasets (fact_* primary, dim_* for JOINs)
    python dataset_discovery.py sources

    # List datasets from Oasis API
    python dataset_discovery.py oasis

    # List BigQuery tables
    python dataset_discovery.py bigquery

    # Get schema for a specific table
    python dataset_discovery.py schema <table_name>

    # Recommend datasets for a use case
    python dataset_discovery.py recommend "ticket metrics over time"
"""

import argparse
import json
import os
import subprocess
import sys
from typing import Dict, List, Optional, Any

# Import stock datasets as fallback
from stock_datasets import FACT_TABLES, DIM_TABLES, print_tables


def list_oasis_datasets(env_file: Optional[str] = None) -> Optional[List[Dict]]:
    """
    List datasets from Oasis API.

    Returns list of datasets or None if API call fails.
    """
    try:
        from devrev_api import DevRevAPIClient
        client = DevRevAPIClient(env_file=env_file)
        result = client.get("oasis.dataset.list")
        return result.get("datasets", [])
    except Exception as e:
        print(f"Warning: Could not fetch from Oasis API: {e}", file=sys.stderr)
        return None


def list_bigquery_tables() -> Optional[List[Dict]]:
    """
    List tables from BigQuery us_east1_devrev dataset.

    Returns list of tables or None if bq command fails.
    """
    try:
        result = subprocess.run(
            ["bq", "ls", "--format=json", "app-devrev-dev:us_east1_devrev"],
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode != 0:
            print(f"Warning: bq ls failed: {result.stderr}", file=sys.stderr)
            return None

        tables = json.loads(result.stdout)
        return tables
    except FileNotFoundError:
        print("Warning: bq command not found. Install Google Cloud SDK.", file=sys.stderr)
        return None
    except subprocess.TimeoutExpired:
        print("Warning: bq command timed out.", file=sys.stderr)
        return None
    except json.JSONDecodeError as e:
        print(f"Warning: Could not parse bq output: {e}", file=sys.stderr)
        return None


def get_bigquery_schema(table_name: str) -> Optional[Dict]:
    """
    Get schema for a specific BigQuery table.

    Returns schema dict or None if command fails.
    """
    try:
        result = subprocess.run(
            ["bq", "show", "--schema", "--format=prettyjson",
             f"app-devrev-dev:us_east1_devrev.{table_name}"],
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode != 0:
            print(f"Error: Could not get schema for {table_name}: {result.stderr}", file=sys.stderr)
            return None

        schema = json.loads(result.stdout)
        return schema
    except FileNotFoundError:
        print("Error: bq command not found. Install Google Cloud SDK.", file=sys.stderr)
        return None
    except subprocess.TimeoutExpired:
        print("Error: bq command timed out.", file=sys.stderr)
        return None
    except json.JSONDecodeError as e:
        print(f"Error: Could not parse schema: {e}", file=sys.stderr)
        return None


def categorize_tables(tables: List[Dict]) -> Dict[str, List[Dict]]:
    """
    Categorize tables into fact_*, dim_*, and other.
    """
    categorized = {
        "fact": [],  # Primary sources for aggregation
        "dim": [],   # For JOIN enrichment only
        "other": []  # Custom or other tables
    }

    for table in tables:
        name = table.get("tableReference", {}).get("tableId", "") or table.get("name", "")
        if name.startswith("fact_"):
            categorized["fact"].append(table)
        elif name.startswith("dim_"):
            categorized["dim"].append(table)
        else:
            categorized["other"].append(table)

    return categorized


def recommend_datasets(use_case: str) -> Dict[str, Any]:
    """
    Recommend datasets based on use case description.

    Returns dict with primary source recommendations and optional JOINs.
    """
    use_case_lower = use_case.lower()

    recommendations = {
        "primary_source": None,
        "join_tables": [],
        "reasoning": ""
    }

    # Keyword matching for primary fact tables
    fact_keywords = {
        "fact_ticket": ["ticket", "support", "sla", "stage", "severity", "case"],
        "fact_events": ["event", "action", "activity", "audit", "log"],
        "fact_timeline": ["timeline", "comment", "update", "history", "activity"],
        "fact_issue": ["issue", "bug", "engineering", "sprint", "development"],
        "fact_conversation": ["conversation", "chat", "message", "channel"],
        "fact_ticket_stage_transitions": ["transition", "stage change", "workflow", "sla breach"],
    }

    # Score each fact table
    scores = {}
    for table, keywords in fact_keywords.items():
        score = sum(1 for kw in keywords if kw in use_case_lower)
        if score > 0:
            scores[table] = score

    if scores:
        best_match = max(scores, key=scores.get)
        recommendations["primary_source"] = best_match

        # Find matching fact table details
        for ft in FACT_TABLES:
            if ft["name"] == best_match:
                recommendations["reasoning"] = f"Based on keywords in your use case, {best_match} is recommended. {ft['description']}"
                break
    else:
        recommendations["primary_source"] = "fact_ticket"
        recommendations["reasoning"] = "No specific keywords matched. fact_ticket is the most commonly used source for custom datasets."

    # Suggest JOIN tables based on use case
    join_keywords = {
        "dim_account": ["account", "customer", "company", "organization"],
        "dim_revu": ["user", "contact", "customer user", "rev user"],
        "dim_devu": ["agent", "assignee", "internal user", "dev user", "employee"],
        "dim_group": ["team", "group", "department"],
        "dim_product": ["product", "part", "feature"],
    }

    for table, keywords in join_keywords.items():
        if any(kw in use_case_lower for kw in keywords):
            for dt in DIM_TABLES:
                if dt["name"] == table:
                    recommendations["join_tables"].append({
                        "name": table,
                        "use_for": dt["use_for"]
                    })
                    break

    return recommendations


def print_oasis_datasets(datasets: List[Dict]):
    """Print Oasis datasets in formatted output."""
    if not datasets:
        print("No datasets found in Oasis.")
        return

    # Categorize by prefix
    fact_datasets = [d for d in datasets if d.get("dataset_name", "").startswith("fact_")]
    dim_datasets = [d for d in datasets if d.get("dataset_name", "").startswith("dim_")]
    custom_datasets = [d for d in datasets if not d.get("dataset_name", "").startswith(("fact_", "dim_"))]

    if fact_datasets:
        print("=== Fact Datasets (Primary Sources) ===\n")
        for d in fact_datasets:
            print(f"  {d.get('dataset_name', 'unknown')}")
            if d.get("title"):
                print(f"    Title: {d['title']}")
            if d.get("description"):
                print(f"    {d['description'][:80]}...")
            print()

    if dim_datasets:
        print("=== Dimension Datasets (For JOIN Enrichment) ===\n")
        print("Note: dim_* tables are directly usable in Oasis.\n")
        for d in dim_datasets:
            print(f"  {d.get('dataset_name', 'unknown')}")
            if d.get("title"):
                print(f"    Title: {d['title']}")
            print()

    if custom_datasets:
        print("=== Custom Datasets ===\n")
        for d in custom_datasets:
            print(f"  {d.get('dataset_name', 'unknown')}")
            if d.get("title"):
                print(f"    Title: {d['title']}")
            if d.get("description"):
                print(f"    {d['description'][:80]}")
            print()


def print_bigquery_tables(tables: List[Dict]):
    """Print BigQuery tables in formatted output."""
    if not tables:
        print("No tables found in BigQuery.")
        return

    categorized = categorize_tables(tables)

    print("=== Fact Tables (Primary Sources for Custom Datasets) ===\n")
    if categorized["fact"]:
        for t in categorized["fact"]:
            name = t.get("tableReference", {}).get("tableId", "")
            print(f"  {name}")
    else:
        print("  (none found)")
    print()

    print("=== Dimension Tables (For JOIN Enrichment Only) ===\n")
    print("Note: dim_* tables are directly usable in Oasis.\n")
    if categorized["dim"]:
        for t in categorized["dim"]:
            name = t.get("tableReference", {}).get("tableId", "")
            print(f"  {name}")
    else:
        print("  (none found)")
    print()

    if categorized["other"]:
        print("=== Other Tables ===\n")
        for t in categorized["other"][:20]:  # Limit to 20
            name = t.get("tableReference", {}).get("tableId", "")
            print(f"  {name}")
        if len(categorized["other"]) > 20:
            print(f"  ... and {len(categorized['other']) - 20} more")
        print()


def print_schema(table_name: str, schema: List[Dict]):
    """Print table schema in formatted output."""
    print(f"=== Schema for {table_name} ===\n")

    # Identify likely partition column
    partition_hints = ["created_date", "modified_date", "timestamp", "transition_time", "event_date"]

    for col in schema:
        name = col.get("name", "")
        col_type = col.get("type", "")
        mode = col.get("mode", "NULLABLE")
        description = col.get("description", "")

        # Mark potential partition columns
        partition_marker = " [PARTITION?]" if name in partition_hints else ""

        print(f"  {name}: {col_type}{partition_marker}")
        if mode != "NULLABLE":
            print(f"    Mode: {mode}")
        if description:
            print(f"    {description[:60]}")

    print(f"\nTotal columns: {len(schema)}")


def print_recommendations(recommendations: Dict[str, Any]):
    """Print dataset recommendations."""
    print("=== Dataset Recommendations ===\n")

    print(f"Primary Source: {recommendations['primary_source']}")
    print(f"Reasoning: {recommendations['reasoning']}")
    print()

    if recommendations["join_tables"]:
        print("Suggested JOINs:")
        for jt in recommendations["join_tables"]:
            print(f"  - {jt['name']}: {jt['use_for']}")
    else:
        print("No specific JOIN tables recommended for this use case.")

    print("\n--- Next Steps ---")
    print("1. Run: /dataset-builder:explore schema <table_name>")
    print("2. Design your aggregation query")
    print("3. Run: /dataset-builder:create to generate the job")


def main():
    parser = argparse.ArgumentParser(
        description="Discover available datasets for custom dataset creation",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    subparsers = parser.add_subparsers(dest="command", help="Discovery method")

    # sources - hardcoded stock datasets (default)
    sources_parser = subparsers.add_parser("sources", help="List stock datasets (fact_* and dim_*)")
    sources_parser.add_argument("--type", choices=["all", "fact", "dim"], default="all",
                                help="Filter by table type")

    # oasis - from Oasis API
    oasis_parser = subparsers.add_parser("oasis", help="List datasets from Oasis API")
    oasis_parser.add_argument("--env-file", default=None, help="Path to .env file (auto-searches if not specified)")

    # bigquery - from BigQuery
    bq_parser = subparsers.add_parser("bigquery", help="List tables from BigQuery")

    # schema - get specific table schema
    schema_parser = subparsers.add_parser("schema", help="Get schema for a table")
    schema_parser.add_argument("table_name", help="Table name (e.g., fact_ticket)")

    # recommend - suggest datasets for use case
    recommend_parser = subparsers.add_parser("recommend", help="Get dataset recommendations")
    recommend_parser.add_argument("use_case", help="Description of your use case")

    args = parser.parse_args()

    # Default to sources if no command specified
    if not args.command:
        args.command = "sources"
        args.type = "all"

    if args.command == "sources":
        print_tables(args.type)

    elif args.command == "oasis":
        datasets = list_oasis_datasets(args.env_file)
        if datasets is not None:
            print_oasis_datasets(datasets)
        else:
            print("\nFalling back to hardcoded stock datasets...\n")
            print_tables("all")

    elif args.command == "bigquery":
        tables = list_bigquery_tables()
        if tables is not None:
            print_bigquery_tables(tables)
        else:
            print("\nFalling back to hardcoded stock datasets...\n")
            print_tables("all")

    elif args.command == "schema":
        schema = get_bigquery_schema(args.table_name)
        if schema:
            print_schema(args.table_name, schema)
        else:
            # Try to find in hardcoded list
            for ft in FACT_TABLES + DIM_TABLES:
                if ft["name"] == args.table_name:
                    print(f"=== Known Columns for {args.table_name} ===\n")
                    print(f"Description: {ft['description']}")
                    print(f"\nCommon columns: {', '.join(ft.get('common_columns', []))}")
                    if 'partition_column' in ft:
                        print(f"Partition column: {ft['partition_column']}")
                    print("\nRun with BigQuery access for full schema.")
                    break
            else:
                print(f"Table {args.table_name} not found in hardcoded list.")

    elif args.command == "recommend":
        recommendations = recommend_datasets(args.use_case)
        print_recommendations(recommendations)


if __name__ == "__main__":
    main()
