#!/usr/bin/env python3
"""
Validate DevRev Widget

Three-stage validation pipeline:
1. Structure validation (mosaic-schema.yaml) - Always runs, errors block
2. Semantic validation (business rules) - Always runs, warnings only
3. API validation (DevRev endpoint) - FINAL AUTHORITY

Structure validation uses DynamicValidator with mosaic-client schema.
Semantic checks produce warnings only.
API validation is the final authority and determines pass/fail.
"""

import sys
import json
import os
import time
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

# Check for required dependencies before proceeding
def check_dependencies():
    """
    Check if all required dependencies are installed.

    Returns:
        Tuple of (all_installed: bool, missing: List[str])
    """
    required_packages = {
        'yaml': 'pyyaml',
        'jsonschema': 'jsonschema',
        'sqlglot': 'sqlglot',
        'duckdb': 'duckdb',
        'requests': 'requests',
        'aiohttp': 'aiohttp',
        'aiofiles': 'aiofiles',
        'pyarrow': 'pyarrow'
    }

    missing = []
    for import_name, package_name in required_packages.items():
        try:
            __import__(import_name)
        except ImportError:
            missing.append(package_name)

    return len(missing) == 0, missing

# Check dependencies first
all_deps_installed, missing_deps = check_dependencies()
if not all_deps_installed:
    print(json.dumps({
        "valid": False,
        "stage_failed": "dependencies",
        "errors": [{
            "rule_id": "MISSING_DEPENDENCIES",
            "severity": "error",
            "field_path": "",
            "message": f"Missing required Python dependencies: {', '.join(missing_deps)}",
            "suggestion": (
                "Install missing dependencies:\n"
                "  Option 1 (recommended): Re-run workspace init:\n"
                "    cd <workspace-root> && dashboard-sync init\n"
                "  Option 2: Manual installation to system Python:\n"
                f"    python3 -m pip install --user {' '.join(missing_deps)}\n"
                "  Option 3: Install from plugin requirements file:\n"
                "    python3 -m pip install --user -r ${CLAUDE_PLUGIN_ROOT}/scripts/widget/requirements.txt"
            )
        }],
        "warnings": []
    }, indent=2))
    sys.exit(2)  # Exit code 2 indicates blocking error (not validation failure)

# Add lib directories to path
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent / 'common' / 'lib'))

from lib.validators import DynamicValidator, SemanticValidator, APIValidator
from lib.core.models import ValidationResult, ValidationError
from lib.debug_logger import DebugLogger
from logger import (
    error, warn, success, result, info, progress,
    add_verbosity_args, apply_verbosity_args, get_verbosity, QUIET
)

# Critical semantic rules that block validation (prevent runtime errors)
CRITICAL_RULES = {
    'SQL_SCHEMA',
    'SQL_EXECUTION',
    'CHART_ARRAY_STRUCTURE',
    'METRIC_VISUALIZATION_STRUCTURE',  # Metric.y must be array for forEach()
    'DATASET_PERMISSION_DENIED',
    'CATALOG_ERROR',  # Missing dataset in organization catalog
    'WINDOW_FUNCTION_IN_OASIS',  # Window functions must be in meerkat layer
    'MEERKAT_PLACEHOLDER_INVALID',  # {MEERKAT} outside OVER() causes parser error
    'SQL_PATTERN_INVALID_ARRAY_CAST',  # Invalid AS TYPE[] syntax
    'FIELD_SCHEMA_DISPLAY_NAME_LOCATION',  # display_name at wrong location
    'FIELD_SCHEMA_TYPE_VS_FIELD_TYPE',  # type vs field_type confusion
    'FIELD_SCHEMA_COLUMN_VS_SQL_EXPRESSION',  # column vs sql_expression confusion
    'FIELD_SCHEMA_DIRECTION_ENUM',  # Invalid direction enum values
    'FIELD_SCHEMA_MISSING_FIELD_TYPE',  # Missing required field_type
    # Type and function validation (prevent runtime errors)
    'UNSUPPORTED_CAST_TYPE',  # CAST to unsupported type (e.g., ARRAY<JSON>)
    'UNSUPPORTED_MEERKAT_FUNCTION',  # Function not supported in Meerkat (e.g., PERCENTILE_CONT)
    'UNSUPPORTED_UNNEST_PARAMETER',  # UNNEST with unsupported parameters (e.g., recursive := true)
    'UNSUPPORTED_UNNEST_JSON',  # UNNEST on JSON type (must use array types)
    'UNSUPPORTED_UNNEST_JSON_EXTRACT',  # UNNEST on json_extract() result (implicit JSON type)
    # Enum validation (prevent HTTP 406 errors from protobuf validator)
    'INVALID_MEERKAT_FUNCTION_TYPE_ENUM',  # Invalid function.type enum (e.g., "MEDIAN" instead of "MeerkatWidgetColumnFunction_TypeEnumMedian")
    'INVALID_WIDGET_VERSION',  # Invalid widget version enum
    'INVALID_MEERKAT_PROJECTION_TYPE',  # Invalid meerkat_schema.type enum. Valid: string, boolean, number, time, string_array, number_array
    # Structural validation (prevent API rejections)
    'MISSING_NAME_FIELD',  # Widget must have 'name' field
    'INVALID_REFERENCE_ID_PATTERN',  # reference_id must match ^[a-zA-Z][a-zA-Z0-9_]*$
    'INVALID_FIELD',  # Invalid fields (unit, sorts, angle) that don't exist in API
    'MISSING_LAYOUT_FIELD',  # Widget must have 'layout' field
}


def load_credentials(workspace_dir: Path) -> Tuple[Optional[str], Optional[str]]:
    """
    Load credentials from workspace .env file.

    Args:
        workspace_dir: Path to workspace directory

    Returns:
        Tuple of (pat, endpoint), both may be None if not found
    """
    env_file = workspace_dir / ".env"
    if not env_file.exists():
        return None, None

    pat = None
    endpoint = None

    try:
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '=' in line:
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip()
                if key == 'DEVREV_PAT':
                    pat = value
                elif key == 'DEVREV_ENDPOINT':
                    endpoint = value
    except Exception:
        pass

    return pat, endpoint


def is_quiet_mode() -> bool:
    """Check if quiet/JSON mode is enabled."""
    return get_verbosity() == QUIET or os.getenv('DASHBOARD_DEV_QUIET', '').lower() in ('1', 'true', 'yes')


def output_error(msg: str, quiet_mode: bool):
    """Output error in appropriate format."""
    if quiet_mode:
        output = {
            "valid": False,
            "stage_failed": "parse",
            "errors": [{
                "rule_id": "PARSE_ERROR",
                "severity": "error",
                "field_path": "",
                "message": msg
            }],
            "warnings": []
        }
        print(json.dumps(output, indent=2))
    else:
        error(msg)


def output_result(validation_result: ValidationResult, quiet_mode: bool):
    """Output validation result in appropriate format."""
    if quiet_mode:
        print(json.dumps(validation_result.to_dict(), indent=2))
    else:
        stage_name = validation_result.stage.value.title()
        error(f"\n{stage_name} Validation Failed ({validation_result.error_count} errors)\n")

        for err in validation_result.errors:
            if err.field_path:
                result(f"  {err.field_path}")
            result(f"    [{err.rule_id}] {err.message}")
            if err.suggestion:
                result(f"    → {err.suggestion}")
            result("")


def output_final_result(
    valid: bool,
    stage_failed: Optional[str],
    errors: List[ValidationError],
    warnings: List[ValidationError],
    quiet_mode: bool
):
    """Output final validation result."""
    if quiet_mode:
        output = {
            "valid": valid,
            "stage_failed": stage_failed,
            "errors": [e.to_dict() for e in errors],
            "warnings": [w.to_dict() for w in warnings]
        }
        print(json.dumps(output, indent=2))
    else:
        if valid:
            if warnings:
                success(f"\nWidget is valid! ({len(warnings)} warnings)")
                for w in warnings:
                    warn(f"  [{w.rule_id}] {w.message}")
                    if w.suggestion:
                        info(f"    → {w.suggestion}")
            else:
                success("\nWidget is valid!")


def run_structure_validation(
    widget: Dict[str, Any],
    quiet_mode: bool,
    debug_logger: Optional[DebugLogger]
) -> Tuple[bool, ValidationResult]:
    """
    Run structure validation stage.

    Returns:
        Tuple of (passed, result)
    """
    if not quiet_mode:
        progress("Stage 1: Structure Validation")

    structure_validator = DynamicValidator(object_type="widget")
    structure_result = structure_validator.validate(widget)

    if debug_logger:
        try:
            debug_logger.log_stage_result("structure", structure_result)
        except Exception:
            pass

    if not structure_result.valid:
        # Check for validation loop
        if debug_logger:
            try:
                loop_info = debug_logger.check_for_validation_loop(structure_result.errors)
                if loop_info:
                    # Add loop warning to help diagnose the issue
                    loop_warning = ValidationError(
                        rule_id=loop_info["type"],
                        severity="warning",
                        field_path="",
                        message=loop_info["message"],
                        suggestion=loop_info["suggestion"]
                    )
                    structure_result.warnings.append(loop_warning)
                    if not quiet_mode:
                        warn(f"\n⚠️  VALIDATION LOOP DETECTED: {loop_info['message']}")
                        info(f"   {loop_info['suggestion']}")
                        if loop_info.get('occurrences'):
                            info(f"   ({loop_info['occurrences']} occurrences in last 30 minutes)")
            except Exception:
                pass

        output_result(structure_result, quiet_mode)
        return False, structure_result

    if not quiet_mode:
        success("Structure valid\n")

    return True, structure_result


def run_semantic_validation(
    widget: Dict[str, Any],
    workspace_dir: Path,
    pat: Optional[str],
    endpoint: Optional[str],
    quiet_mode: bool,
    debug_logger: Optional[DebugLogger]
) -> Tuple[bool, List[ValidationError], List[ValidationError]]:
    """
    Run semantic validation stage.

    Returns:
        Tuple of (passed, critical_errors, warnings)
    """
    if not quiet_mode:
        progress("Stage 2: Semantic Validation")

    semantic_validator = SemanticValidator(
        workspace_path=workspace_dir,
        pat=pat,
        endpoint=endpoint
    )
    semantic_result = semantic_validator.validate(widget)

    if debug_logger:
        try:
            debug_logger.log_stage_result("semantic", semantic_result)
        except Exception:
            pass

    # Collect warnings
    all_warnings = list(semantic_result.warnings)

    if not semantic_result.valid:
        # Separate critical from non-critical errors
        critical_errors = [e for e in semantic_result.errors if e.rule_id in CRITICAL_RULES]
        non_critical_errors = [e for e in semantic_result.errors if e.rule_id not in CRITICAL_RULES]

        if critical_errors:
            # Critical errors block validation
            if not quiet_mode:
                error(f"Critical semantic errors ({len(critical_errors)} issues)")
                for err in critical_errors:
                    result(f"    - [{err.rule_id}] {err.message}")
                    if err.suggestion:
                        result(f"      → {err.suggestion}")
            return False, critical_errors, all_warnings + non_critical_errors

        # Non-critical errors become warnings
        if non_critical_errors:
            if not quiet_mode:
                warn(f"Semantic warnings ({len(non_critical_errors)} issues)")
                for err in non_critical_errors:
                    result(f"    - [{err.rule_id}] {err.message}")
                    if err.suggestion:
                        result(f"      → {err.suggestion}")
            for err in non_critical_errors:
                err.severity = "warning"
                all_warnings.append(err)
    else:
        if not quiet_mode:
            if semantic_result.warning_count > 0:
                success(f"Semantic rules passed ({semantic_result.warning_count} warnings)")
                for w in semantic_result.warnings:
                    warn(f"  [{w.rule_id}] {w.message}")
                    if w.suggestion:
                        info(f"    → {w.suggestion}")
                print()
            else:
                success("All semantic rules passed\n")

    return True, [], all_warnings


def run_api_validation(
    widget: Dict[str, Any],
    workspace_dir: Path,
    all_warnings: List[ValidationError],
    quiet_mode: bool,
    debug_logger: Optional[DebugLogger]
) -> Tuple[bool, Optional[ValidationResult]]:
    """
    Run API validation stage.

    Returns:
        Tuple of (passed, result)
    """
    if not quiet_mode:
        progress("Stage 3: API Validation (Final Authority)")

    env_file = workspace_dir / ".env"

    if not env_file.exists():
        error_msg = f".env file not found: {env_file}"
        if quiet_mode:
            output = {
                "valid": False,
                "stage_failed": "api",
                "errors": [{
                    "rule_id": "API_CREDENTIALS",
                    "severity": "error",
                    "field_path": "",
                    "message": error_msg,
                    "suggestion": "Create .env file with DEVREV_PAT and DEVREV_ENDPOINT, or use --skip-api"
                }],
                "warnings": [w.to_dict() for w in all_warnings]
            }
            print(json.dumps(output, indent=2))
        else:
            error(f"  {error_msg}")
            info("     Create .env file with DEVREV_PAT and DEVREV_ENDPOINT, or use --skip-api")
        return False, None

    try:
        api_validator = APIValidator(env_file=env_file)
        api_result = api_validator.validate(widget)

        if debug_logger:
            try:
                debug_logger.log_stage_result("api", api_result)
            except Exception:
                pass

        if not api_result.valid:
            # Check for validation loop
            if debug_logger:
                try:
                    loop_info = debug_logger.check_for_validation_loop(api_result.errors)
                    if loop_info:
                        loop_warning = ValidationError(
                            rule_id=loop_info["type"],
                            severity="warning",
                            field_path="",
                            message=loop_info["message"],
                            suggestion=loop_info["suggestion"]
                        )
                        all_warnings.append(loop_warning)
                        if not quiet_mode:
                            warn(f"\n⚠️  VALIDATION LOOP DETECTED: {loop_info['message']}")
                            info(f"   {loop_info['suggestion']}")
                            if loop_info.get('occurrences'):
                                info(f"   ({loop_info['occurrences']} occurrences in last 30 minutes)")
                except Exception:
                    pass

            if quiet_mode:
                output = api_result.to_dict()
                output["warnings"] = [w.to_dict() for w in all_warnings]
                print(json.dumps(output, indent=2))
            else:
                output_result(api_result, quiet_mode)
                if all_warnings:
                    warn(f"\n  Also had {len(all_warnings)} semantic warnings:")
                    for w in all_warnings:
                        warn(f"    [{w.rule_id}] {w.message}")
            return False, api_result

        if not quiet_mode:
            success("API validation passed\n")

        return True, api_result

    except Exception as e:
        if debug_logger:
            try:
                debug_logger.log_exception(e, "api_call")
            except Exception:
                pass
        error_msg = f"API validation error: {e}"
        if quiet_mode:
            output = {
                "valid": False,
                "stage_failed": "api",
                "errors": [{
                    "rule_id": "API_ERROR",
                    "severity": "error",
                    "field_path": "",
                    "message": error_msg,
                    "suggestion": "Check .env credentials and network connectivity"
                }],
                "warnings": [w.to_dict() for w in all_warnings]
            }
            print(json.dumps(output, indent=2))
        else:
            error(f"  {error_msg}")
        return False, None


def validate_widget(
    workspace_path: str,
    widget_file: str,
    skip_api: bool = False,
    no_debug_log: bool = False
) -> int:
    """
    Validate widget JSON through three-stage pipeline.

    Structure validation must pass.
    Semantic validation produces warnings only.
    API validation is the FINAL AUTHORITY.

    Args:
        workspace_path: Path to workspace directory
        widget_file: Widget JSON file path (relative to workspace)
        skip_api: Skip API validation (default: False)
        no_debug_log: Disable debug logging (default: False)

    Returns:
        Exit code: 0 if valid, 1 if invalid
    """
    validation_start_time = time.time()
    workspace_dir = Path(workspace_path).expanduser().resolve()
    widget_path = workspace_dir / widget_file
    quiet_mode = is_quiet_mode()

    # Initialize debug logger
    debug_logger = None
    if not no_debug_log:
        try:
            debug_logger = DebugLogger(workspace_path=workspace_dir, enabled=True)
            debug_logger.log_validation_start(
                widget_path=str(widget_file),
                mode="skip_api" if skip_api else "full_with_api"
            )
        except Exception as e:
            error(f"Failed to initialize debug logger: {e}")

    # Load widget file
    if not widget_path.exists():
        output_error(f"Widget file not found: {widget_path}", quiet_mode)
        return 1

    try:
        with open(widget_path) as f:
            widget = json.load(f)
    except json.JSONDecodeError as e:
        if debug_logger:
            try:
                debug_logger.log_exception(e, "json_parse")
            except Exception:
                pass
        output_error(f"Invalid JSON: {e}", quiet_mode)
        return 1
    except Exception as e:
        if debug_logger:
            try:
                debug_logger.log_exception(e, "json_load")
            except Exception:
                pass
        output_error(f"Failed to load widget: {e}", quiet_mode)
        return 1

    if not quiet_mode:
        result(f"Validating widget: {widget.get('title', 'Untitled')}")
        info(f"   File: {widget_path}")
        info("   Mode: API is final authority (semantic are warnings)\n")

    # Load credentials
    pat, endpoint = load_credentials(workspace_dir)

    # Stage 1: Structure Validation
    passed, _ = run_structure_validation(widget, quiet_mode, debug_logger)
    if not passed:
        if debug_logger:
            try:
                debug_logger.log_validation_end(
                    total_duration=time.time() - validation_start_time,
                    final_result=False
                )
            except Exception:
                pass
        return 1

    # Stage 2: Semantic Validation
    passed, critical_errors, all_warnings = run_semantic_validation(
        widget, workspace_dir, pat, endpoint, quiet_mode, debug_logger
    )
    if not passed:
        output_final_result(False, "semantic", critical_errors, all_warnings, quiet_mode)
        if debug_logger:
            try:
                debug_logger.log_validation_end(
                    total_duration=time.time() - validation_start_time,
                    final_result=False
                )
            except Exception:
                pass
        return 1

    # Stage 3: API Validation
    if not skip_api:
        passed, _ = run_api_validation(
            widget, workspace_dir, all_warnings, quiet_mode, debug_logger
        )
        if not passed:
            if debug_logger:
                try:
                    debug_logger.log_validation_end(
                        total_duration=time.time() - validation_start_time,
                        final_result=False
                    )
                except Exception:
                    pass
            return 1
    else:
        if not quiet_mode:
            info("Stage 3: API Validation [SKIPPED]\n")
            if all_warnings:
                warn(f"{len(all_warnings)} semantic warnings (API not run to verify):")
                for w in all_warnings:
                    warn(f"  [{w.rule_id}] {w.message}")
                    if w.suggestion:
                        info(f"    → {w.suggestion}")

    # All stages passed
    output_final_result(True, None, [], all_warnings, quiet_mode)

    if debug_logger:
        try:
            debug_logger.log_validation_end(
                total_duration=time.time() - validation_start_time,
                final_result=True
            )
            debug_logger.rotate_logs()
        except Exception:
            pass

    return 0


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description='Validate DevRev widget JSON',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Validation Philosophy:
  - Structure validation: Must pass (checks JSON structure)
  - Semantic validation: Warnings only (checks business rules)
  - API validation: FINAL AUTHORITY (DevRev server decides)

Examples:
  python validate_widget.py . widgets/my-widget.json
  python validate_widget.py . widgets/my-widget.json --skip-api
  python validate_widget.py . widgets/my-widget.json --quiet
        """
    )

    parser.add_argument('workspace_path', help='Path to workspace directory')
    parser.add_argument('widget', help='Widget JSON file (relative to workspace)')
    parser.add_argument('--skip-api', action='store_true', help='Skip API validation')
    parser.add_argument('--no-debug-log', action='store_true', help='Disable debug logging')
    add_verbosity_args(parser)

    args = parser.parse_args()
    apply_verbosity_args(args)

    try:
        exit_code = validate_widget(
            workspace_path=args.workspace_path,
            widget_file=args.widget,
            skip_api=args.skip_api,
            no_debug_log=args.no_debug_log
        )
        sys.exit(exit_code)
    except KeyboardInterrupt:
        if not is_quiet_mode():
            warn("\nInterrupted")
        sys.exit(130)


if __name__ == '__main__':
    main()
