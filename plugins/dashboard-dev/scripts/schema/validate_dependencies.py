#!/usr/bin/env python3
"""
Validate Widget Dependencies

Preflight validation that ALL widget dependencies (datasets, schemas, dimensions) exist.
Hard fails if ANY dependency is missing.

Usage:
    python validate_dependencies.py <workspace_path> --widget widgets/foo.json
    python validate_dependencies.py <workspace_path> --datasets dim_ticket,dim_account
    python validate_dependencies.py <workspace_path> --datasets "dim_ticket,dim_account" --json

Exit Codes:
    0: All dependencies valid
    1: Missing dependencies (fail-fast)
"""

import sys
import json
import argparse
from pathlib import Path
from typing import Dict, List, Any, Optional

# Add common lib directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'common' / 'lib'))

from logger import (
    error, result, warn, info, success, progress,
    add_verbosity_args, apply_verbosity_args, get_verbosity, QUIET
)


def ensure_prefix(dataset_name: str) -> str:
    """Ensure dataset has devrev. prefix."""
    if not dataset_name.startswith('devrev.'):
        return f'devrev.{dataset_name}'
    return dataset_name


def get_schema_file(workspace_dir: Path, dataset_name: str) -> Path:
    """Get schema file path from datasets/ directory.

    Supports both new naming (devrev.dataset.yaml) and legacy naming (*-analyzed.yaml).
    """
    full_name = ensure_prefix(dataset_name)
    schema_dir = workspace_dir / "datasets"

    # Try new naming first (clean, no -analyzed postfix)
    new_path = schema_dir / f"{full_name}.yaml"
    if new_path.exists():
        return new_path

    # Fall back to legacy naming (with -analyzed postfix)
    legacy_path = schema_dir / f"{full_name}-analyzed.yaml"
    if legacy_path.exists():
        return legacy_path

    # Also try old format without prefix for legacy workspaces
    old_name = dataset_name.replace('devrev.', '')
    old_path = schema_dir / f"{old_name}-analyzed.yaml"
    if old_path.exists():
        return old_path

    # Return expected path (new format)
    return new_path


def extract_datasets_from_widget(widget: Dict[str, Any]) -> List[str]:
    """Extract all dataset names from a widget JSON."""
    datasets = []

    for data_source in widget.get('data_sources', []):
        oasis = data_source.get('oasis', {})
        ds_list = oasis.get('datasets', [])
        datasets.extend(ds_list)

    # Deduplicate while preserving order
    seen = set()
    unique_datasets = []
    for ds in datasets:
        if ds not in seen:
            seen.add(ds)
            unique_datasets.append(ds)

    return unique_datasets


def validate_datasets(workspace_path: str, datasets: List[str]) -> Dict[str, Any]:
    """
    Validate that all dataset schemas exist.

    Args:
        workspace_path: Path to workspace directory
        datasets: List of dataset names to validate

    Returns:
        Dictionary with validation results
    """
    workspace_dir = Path(workspace_path).expanduser().resolve()

    results = {
        "valid": True,
        "total_datasets": len(datasets),
        "missing_count": 0,
        "cached_count": 0,
        "datasets": [],
        "missing_schemas": [],
        "error": None
    }

    for dataset in datasets:
        full_name = ensure_prefix(dataset)
        schema_file = get_schema_file(workspace_dir, full_name)

        ds_result = {
            "name": full_name,
            "schema_file": str(schema_file.relative_to(workspace_dir)) if schema_file.exists() else None,
            "cached": schema_file.exists()
        }
        results["datasets"].append(ds_result)

        if schema_file.exists():
            results["cached_count"] += 1
        else:
            results["missing_count"] += 1
            results["missing_schemas"].append(full_name)
            results["valid"] = False

    return results


def validate_widget_file(workspace_path: str, widget_file: str) -> Dict[str, Any]:
    """
    Validate all dependencies for a widget JSON file.

    Args:
        workspace_path: Path to workspace directory
        widget_file: Path to widget JSON file (relative to workspace)

    Returns:
        Dictionary with validation results
    """
    workspace_dir = Path(workspace_path).expanduser().resolve()
    widget_path = workspace_dir / widget_file

    if not widget_path.exists():
        return {
            "valid": False,
            "error": f"Widget file not found: {widget_path}",
            "missing_schemas": [],
            "datasets": []
        }

    try:
        with open(widget_path) as f:
            widget = json.load(f)
    except json.JSONDecodeError as e:
        return {
            "valid": False,
            "error": f"Invalid JSON in widget file: {e}",
            "missing_schemas": [],
            "datasets": []
        }

    # Extract datasets from widget
    datasets = extract_datasets_from_widget(widget)

    if not datasets:
        return {
            "valid": False,
            "error": "No datasets found in widget (missing data_sources[].oasis.datasets)",
            "missing_schemas": [],
            "datasets": []
        }

    # Validate all datasets
    validation_result = validate_datasets(workspace_path, datasets)
    validation_result["widget_file"] = widget_file
    validation_result["widget_title"] = widget.get("title", "Untitled")

    return validation_result


def output_result(validation: Dict[str, Any], quiet_mode: bool):
    """Output validation result in appropriate format."""
    if quiet_mode:
        print(json.dumps(validation, indent=2))
        return

    # Terminal output - use print for consistent ordering
    if validation.get("widget_file"):
        print(f"Widget: {validation.get('widget_title', 'Untitled')}")
        print(f"   File: {validation['widget_file']}")

    print(f"\nDataset Dependencies: {validation['total_datasets']} total")

    for ds in validation.get("datasets", []):
        status = "CACHED" if ds["cached"] else "MISSING"
        icon = "[ok]" if ds["cached"] else "[X]"
        print(f"   {icon} {ds['name']}: {status}")

    print("")
    sys.stdout.flush()  # Ensure output order with stderr

    if validation["valid"]:
        success(f"All {validation['cached_count']} schema(s) available")
    else:
        print(f"BLOCKED: {validation['missing_count']} schema(s) missing", file=sys.stderr)
        print("")
        print("To download missing schemas:")
        for missing in validation["missing_schemas"]:
            print(f"   dashboard-sync dataset fetch {missing}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Validate widget dependencies (fail-fast)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Validates that ALL required schemas exist before widget generation.
Returns exit code 1 if ANY dependency is missing.

Examples:
  # Validate widget file
  python validate_dependencies.py . --widget widgets/my-widget.json

  # Validate dataset list
  python validate_dependencies.py . --datasets dim_ticket,dim_account

  # JSON output for parsing
  python validate_dependencies.py . --widget widgets/foo.json --json
        """
    )

    parser.add_argument('workspace_path', help='Path to workspace directory')

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--widget', '-w', help='Widget JSON file (relative to workspace)')
    group.add_argument('--datasets', '-d', help='Comma-separated list of dataset names')

    parser.add_argument('--json', action='store_true', help='Output as JSON')
    add_verbosity_args(parser)

    args = parser.parse_args()
    apply_verbosity_args(args)

    quiet_mode = args.json or get_verbosity() == QUIET

    try:
        if args.widget:
            validation = validate_widget_file(args.workspace_path, args.widget)
        else:
            datasets = [ds.strip() for ds in args.datasets.split(',') if ds.strip()]
            if not datasets:
                error("No datasets provided")
                sys.exit(1)
            validation = validate_datasets(args.workspace_path, datasets)

        output_result(validation, quiet_mode)

        # Exit code based on validation result
        sys.exit(0 if validation["valid"] else 1)

    except KeyboardInterrupt:
        warn("\nInterrupted")
        sys.exit(130)
    except Exception as e:
        if quiet_mode:
            print(json.dumps({"valid": False, "error": str(e)}, indent=2))
        else:
            error(f"Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
