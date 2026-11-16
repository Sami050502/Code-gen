#!/usr/bin/env python3
"""
Stock datasets configuration for dataset-builder plugin.

Lists available stock datasets in DevRev's Oasis platform.

IMPORTANT:
- fact_* tables: PRIMARY and ONLY sources for custom dataset aggregation
- dim_* tables: For JOIN enrichment ONLY (already directly usable in Oasis)

DO NOT create custom datasets from dim_* tables - they are already in Oasis!
"""

# Fact tables - PRIMARY sources for custom datasets (time-partitioned, historical)
# These contain HISTORICAL data and should be your aggregation source
FACT_TABLES = [
    {
        "name": "fact_ticket",
        "description": "Ticket events over time - SLA, stage transitions, updates",
        "common_columns": ["id", "dev_oid", "created_date", "modified_date", "stage", "severity"],
        "partition_column": "created_date",
        "use_for": "Ticket metrics, stage history, SLA tracking",
    },
    {
        "name": "fact_events",
        "description": "General platform events - user actions, system events",
        "common_columns": ["id", "dev_oid", "event_type", "timestamp", "actor_id"],
        "partition_column": "timestamp",
        "use_for": "Activity tracking, audit trails, event analytics",
    },
    {
        "name": "fact_timeline",
        "description": "Timeline events - comments, updates, activities",
        "common_columns": ["id", "dev_oid", "object_id", "event_type", "created_date"],
        "partition_column": "created_date",
        "use_for": "Activity feeds, engagement metrics",
    },
    {
        "name": "fact_issue",
        "description": "Issue events over time - engineering workflow, stage history",
        "common_columns": ["id", "dev_oid", "issue_id", "created_date", "modified_date", "stage", "from_stage", "to_stage"],
        "partition_column": "created_date",
        "use_for": "Issue stage history, engineering metrics, cycle time",
    },
    {
        "name": "fact_conversation",
        "description": "Conversation metrics - support interactions",
        "common_columns": ["id", "dev_oid", "created_date", "channel", "status"],
        "partition_column": "created_date",
        "use_for": "Conversation analytics, channel metrics",
    },
    {
        "name": "fact_ticket_stage_transitions",
        "description": "Ticket stage change history - SLA tracking",
        "common_columns": ["id", "dev_oid", "ticket_id", "from_stage", "to_stage", "transition_time"],
        "partition_column": "transition_time",
        "use_for": "Stage duration, SLA breach tracking, workflow analysis",
    },
]

# Dimension tables - For JOIN enrichment only (already directly usable in Oasis)
DIM_TABLES = [
    {
        "name": "dim_ticket",
        "description": "Current ticket state - support tickets",
        "common_columns": ["id", "dev_oid", "title", "status", "severity", "account_id", "assignee_id"],
        "use_for": "JOIN to get ticket details, current status",
    },
    {
        "name": "dim_account",
        "description": "Customer accounts",
        "common_columns": ["id", "dev_oid", "name", "tier", "industry"],
        "use_for": "JOIN to get account names and attributes",
    },
    {
        "name": "dim_revu",
        "description": "Customer contacts (rev users)",
        "common_columns": ["id", "dev_oid", "email", "display_name", "account_id"],
        "use_for": "JOIN to get customer contact info",
    },
    {
        "name": "dim_devu",
        "description": "Internal users (dev users)",
        "common_columns": ["id", "dev_oid", "email", "display_name", "department"],
        "use_for": "JOIN to get internal user info",
    },
    {
        "name": "dim_issue",
        "description": "Current issue state - engineering issues",
        "common_columns": ["id", "dev_oid", "title", "status", "priority", "assignee_id"],
        "use_for": "JOIN to get issue details",
    },
    {
        "name": "dim_conversation",
        "description": "Current conversation state",
        "common_columns": ["id", "dev_oid", "title", "channel", "status"],
        "use_for": "JOIN to get conversation details",
    },
    {
        "name": "dim_group",
        "description": "Teams and groups",
        "common_columns": ["id", "dev_oid", "name", "type"],
        "use_for": "JOIN to get team/group info",
    },
    {
        "name": "dim_product",
        "description": "Products and parts",
        "common_columns": ["id", "dev_oid", "name", "type", "parent_id"],
        "use_for": "JOIN to get product info",
    },
]


def get_fact_tables():
    """Get list of fact tables (primary sources for custom datasets)."""
    return FACT_TABLES


def get_dim_tables():
    """Get list of dimension tables (for JOIN enrichment only)."""
    return DIM_TABLES


def get_all_tables():
    """Get all stock tables."""
    return {"fact": FACT_TABLES, "dim": DIM_TABLES}


def print_tables(table_type="all"):
    """Print tables in a formatted way."""
    if table_type in ("all", "fact"):
        print("=== Fact Tables (PRIMARY Sources for Custom Datasets) ===\n")
        print("These contain HISTORICAL data - use these for aggregation!\n")
        for t in FACT_TABLES:
            print(f"  {t['name']}")
            print(f"    {t['description']}")
            print(f"    Partition: {t['partition_column']}")
            if t.get('use_for'):
                print(f"    Best for: {t['use_for']}")
            print()

    if table_type in ("all", "dim"):
        print("=== Dimension Tables (For JOIN Enrichment ONLY) ===\n")
        print("WARNING: Do NOT use dim_* as primary source!")
        print("         dim_* tables are already in Oasis - no custom dataset needed.")
        print("         Use ONLY for JOIN enrichment to get names/attributes.\n")
        for t in DIM_TABLES:
            print(f"  {t['name']}")
            print(f"    {t['description']}")
            print(f"    JOIN for: {t['use_for']}")
            print()


if __name__ == "__main__":
    import sys
    table_type = sys.argv[1] if len(sys.argv) > 1 else "all"
    print_tables(table_type)
