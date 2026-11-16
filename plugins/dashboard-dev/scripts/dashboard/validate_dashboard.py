#!/usr/bin/env python3
"""
Dashboard validation script for DevRev dashboards.

Validates dashboard JSON structure and optionally calls DevRev API for full validation.

Usage:
    python validate_dashboard.py <project_root> <dashboard_file> [--quiet] [--no-api]

Exit codes:
    0: Validation passed
    1: Fatal error (file not found, invalid JSON)
    2: Validation failed (structure or API errors)
"""

import sys
import json
import re
import time
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

# Import debug_logger from widget lib
sys.path.insert(0, str(Path(__file__).parent.parent / 'widget' / 'lib'))
try:
    from debug_logger import DebugLogger
except ImportError:
    DebugLogger = None  # Graceful fallback


# Import DevRev client if available
try:
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from common.lib.devrev_widget_client import DevRevWidgetClient
    API_AVAILABLE = True
except ImportError:
    API_AVAILABLE = False


class ValidationError:
    """Represents a validation error."""

    def __init__(self, code: str, message: str, severity: str = "error"):
        self.code = code
        self.message = message
        self.severity = severity

    def __str__(self):
        return f"[{self.severity.upper()}] {self.code}: {self.message}"


class DashboardValidator:
    """Validates DevRev dashboard JSON."""

    # Constants
    MAX_WIDGETS_TOTAL = 300
    MAX_WIDGETS_PER_TAB = 50
    GRID_COLUMNS = 12
    REQUIRED_VERSION = "v0"

    # DON pattern - accepts both don:data: (current) and don:identity: (legacy)
    DON_PATTERN = re.compile(
        r"^don:(data|identity):[a-z0-9-]+:devo/[A-Za-z0-9_-]+:widget/[A-Za-z0-9_-]+$"
    )

    def __init__(self, dashboard_data: Dict[str, Any], file_path: str):
        self.dashboard = dashboard_data
        self.file_path = file_path
        self.errors: List[ValidationError] = []
        self.warnings: List[ValidationError] = []

    def validate(self, skip_api: bool = False) -> bool:
        """
        Run all validations.

        Args:
            skip_api: If True, skip API validation

        Returns:
            True if validation passed, False otherwise
        """
        # Check for DOWNLOAD format first (fail fast)
        self._validate_format()
        if self.errors:
            return False  # Don't continue if wrong format

        # Structure validation
        self._validate_required_fields()
        self._validate_version()
        self._validate_widget_count()
        self._validate_reference_ids()
        self._validate_layout()
        self._validate_widget_dons()
        self._validate_tab_limits()
        self._validate_hierarchy()

        # API validation (if not skipped and no structure errors)
        if not skip_api and not self.errors and API_AVAILABLE:
            self._validate_via_api()

        return len(self.errors) == 0

    def _validate_format(self):
        """Validate dashboard is in CREATE format, not DOWNLOAD format.

        DOWNLOAD format has an outer wrapper:
        {"dashboard": {"title": "...", "version": "v0", ...}}

        CREATE format has content at root:
        {"title": "...", "version": "v0", ...}
        """
        # Check for outer "dashboard" wrapper
        if "dashboard" in self.dashboard and isinstance(self.dashboard.get("dashboard"), dict):
            inner = self.dashboard["dashboard"]
            # Check if inner object has dashboard content fields
            dashboard_fields = {"title", "version", "layout", "widgets", "tabs", "sections"}
            if any(f in inner for f in dashboard_fields):
                self.errors.append(
                    ValidationError(
                        "DOWNLOAD_FORMAT_DETECTED",
                        "Dashboard is in DOWNLOAD format (wrapped in outer 'dashboard' object). "
                        "Convert to CREATE format by extracting the contents of the 'dashboard' key to the root level.\n\n"
                        "Current (DOWNLOAD format):\n"
                        '  {"dashboard": {"title": "...", "widgets": [...]}}\n\n'
                        "Required (CREATE format):\n"
                        '  {"title": "...", "widgets": [...]}'
                    )
                )
                return

        # Check for platform-only fields at root (indicates downloaded but unwrapped)
        platform_fields = ["id", "display_id", "created_by", "created_date",
                         "modified_by", "modified_date", "object_version"]
        found_platform_fields = [f for f in platform_fields if f in self.dashboard]

        if found_platform_fields and "title" in self.dashboard:
            self.warnings.append(
                ValidationError(
                    "PLATFORM_FIELDS_DETECTED",
                    f"Dashboard contains platform-only fields that should be removed: "
                    f"{', '.join(found_platform_fields)}. "
                    "These are added by the platform during download and may cause issues during create/update.",
                    severity="warning"
                )
            )

    def _validate_required_fields(self):
        """Validate required top-level fields."""
        required = ["title", "version", "layout", "widgets"]

        for field in required:
            if field not in self.dashboard:
                self.errors.append(
                    ValidationError(
                        "MISSING_REQUIRED_FIELD",
                        f"Missing required field: {field}"
                    )
                )

    def _validate_version(self):
        """Validate version field."""
        version = self.dashboard.get("version")

        if version != self.REQUIRED_VERSION:
            self.errors.append(
                ValidationError(
                    "INVALID_VERSION",
                    f"Version must be '{self.REQUIRED_VERSION}', got '{version}'"
                )
            )

    def _validate_widget_count(self):
        """Validate total widget count."""
        widgets = self.dashboard.get("widgets", [])
        count = len(widgets)

        if count > self.MAX_WIDGETS_TOTAL:
            self.errors.append(
                ValidationError(
                    "MAX_WIDGETS_EXCEEDED",
                    f"Dashboard has {count} widgets (max {self.MAX_WIDGETS_TOTAL})"
                )
            )

    def _validate_reference_ids(self):
        """Validate all reference IDs are unique."""
        ref_ids = []

        # Collect all reference IDs
        def collect_refs(layout_items):
            for item in layout_items:
                if "reference_id" in item:
                    ref_ids.append(item["reference_id"])
                if "layout" in item:
                    collect_refs(item["layout"])

        layout = self.dashboard.get("layout", [])
        collect_refs(layout)

        # Check for duplicates
        seen = set()
        for ref_id in ref_ids:
            if ref_id in seen:
                self.errors.append(
                    ValidationError(
                        "DUPLICATE_REFERENCE_ID",
                        f"reference_id '{ref_id}' is used multiple times"
                    )
                )
            seen.add(ref_id)

        # Check all refs have matching component definitions
        widget_refs = {w.get("reference_id") for w in self.dashboard.get("widgets", [])}
        tab_refs = {t.get("reference_id") for t in self.dashboard.get("tabs", [])}
        section_refs = {s.get("reference_id") for s in self.dashboard.get("sections", [])}

        all_component_refs = widget_refs | tab_refs | section_refs

        for ref_id in ref_ids:
            if ref_id not in all_component_refs:
                self.errors.append(
                    ValidationError(
                        "MISSING_COMPONENT_DEFINITION",
                        f"reference_id '{ref_id}' in layout has no matching component definition"
                    )
                )

    def _validate_layout(self):
        """Validate layout positions and grid constraints."""

        def validate_position(item, parent_name="root"):
            ref_id = item.get("reference_id", "unknown")
            position = item.get("position")

            if not position:
                self.errors.append(
                    ValidationError(
                        "MISSING_POSITION",
                        f"Item '{ref_id}' has no position defined"
                    )
                )
                return

            # Check required position fields
            required_pos_fields = ["x", "y", "width", "height"]
            for field in required_pos_fields:
                if field not in position:
                    self.errors.append(
                        ValidationError(
                            "MISSING_POSITION_FIELD",
                            f"Item '{ref_id}' position missing '{field}'"
                        )
                    )
                    return

            x = position["x"]
            y = position["y"]
            width = position["width"]
            height = position["height"]

            # Validate ranges
            if x < 0 or x >= self.GRID_COLUMNS:
                self.errors.append(
                    ValidationError(
                        "INVALID_GRID_X",
                        f"Item '{ref_id}' has invalid x={x} (must be 0-{self.GRID_COLUMNS - 1})"
                    )
                )

            if y < 0:
                self.errors.append(
                    ValidationError(
                        "INVALID_GRID_Y",
                        f"Item '{ref_id}' has invalid y={y} (must be >= 0)"
                    )
                )

            if width < 1 or width > self.GRID_COLUMNS:
                self.errors.append(
                    ValidationError(
                        "INVALID_GRID_WIDTH",
                        f"Item '{ref_id}' has invalid width={width} (must be 1-{self.GRID_COLUMNS})"
                    )
                )

            if height < 1:
                self.errors.append(
                    ValidationError(
                        "INVALID_GRID_HEIGHT",
                        f"Item '{ref_id}' has invalid height={height} (must be >= 1)"
                    )
                )

            # Check grid overflow
            if x + width > self.GRID_COLUMNS:
                self.errors.append(
                    ValidationError(
                        "GRID_OVERFLOW",
                        f"Item '{ref_id}' overflows grid: x={x}, width={width} (x+width={x + width} > {self.GRID_COLUMNS})"
                    )
                )

            # Validate nested layout
            if "layout" in item:
                for nested_item in item["layout"]:
                    validate_position(nested_item, ref_id)

        layout = self.dashboard.get("layout", [])
        for item in layout:
            validate_position(item)

    def _validate_widget_dons(self):
        """Validate widget reference format for CREATE API."""
        widgets = self.dashboard.get("widgets", [])

        for widget_ref in widgets:
            ref_id = widget_ref.get("reference_id", "unknown")

            # Check for WRONG flat widget_id format
            if "widget_id" in widget_ref:
                self.errors.append(
                    ValidationError(
                        "INVALID_WIDGET_FORMAT",
                        f"Widget '{ref_id}' uses 'widget_id' field. "
                        f"CREATE API requires nested format: "
                        f"{{'widget': {{'id': 'don:...'}}}}"
                    )
                )
                continue

            # Check for missing widget field
            if "widget" not in widget_ref:
                self.errors.append(
                    ValidationError(
                        "MISSING_WIDGET_FIELD",
                        f"Widget '{ref_id}' missing 'widget' field"
                    )
                )
                continue

            widget = widget_ref["widget"]

            # Check if widget is an object
            if not isinstance(widget, dict):
                self.errors.append(
                    ValidationError(
                        "INVALID_WIDGET_TYPE",
                        f"Widget '{ref_id}' 'widget' must be an object with 'id' key"
                    )
                )
                continue

            # Check for embedded widget object (DOWNLOAD format)
            embedded_fields = [
                'title', 'data_sources', 'type', 'version',
                'created_by', 'created_date', 'modified_by', 'modified_date',
                'sub_widgets', 'layout', 'description'
            ]
            found_embedded = [f for f in embedded_fields if f in widget]

            if found_embedded:
                self.errors.append(
                    ValidationError(
                        "EMBEDDED_WIDGET_OBJECT",
                        f"Widget '{ref_id}' contains embedded widget object (DOWNLOAD format). "
                        f"Found fields: {', '.join(found_embedded)}. "
                        f"CREATE format requires ID-only reference: "
                        f"{{'widget': {{'id': '{widget.get('id', 'don:...')}'}}}}. "
                        f"Remove all fields except 'id'."
                    )
                )
                continue

            # Check for missing id field
            if "id" not in widget:
                self.errors.append(
                    ValidationError(
                        "MISSING_WIDGET_ID",
                        f"Widget '{ref_id}' 'widget' object missing 'id' field"
                    )
                )
                continue

            # Validate DON format
            widget_id = widget["id"]
            if not self.DON_PATTERN.match(widget_id):
                self.errors.append(
                    ValidationError(
                        "INVALID_WIDGET_DON",
                        f"Widget '{ref_id}' has invalid DON format: {widget_id}. "
                        f"Expected: don:data:region:devo/ORG:widget/ID"
                    )
                )

    def _validate_tab_limits(self):
        """Validate widget count per tab (recursive)."""
        tabs = self.dashboard.get("tabs", [])
        if not tabs:
            return

        layout = self.dashboard.get("layout", [])
        widget_refs = {w.get("reference_id") for w in self.dashboard.get("widgets", [])}

        def count_widgets_recursive(layout_items):
            count = 0
            for item in layout_items:
                ref_id = item.get("reference_id")
                if ref_id in widget_refs:
                    count += 1
                if "layout" in item:
                    count += count_widgets_recursive(item["layout"])
            return count

        # Find each tab in layout and count its widgets
        for tab in tabs:
            tab_ref = tab.get("reference_id")
            tab_layout_item = self._find_layout_item(layout, tab_ref)

            if tab_layout_item and "layout" in tab_layout_item:
                count = count_widgets_recursive(tab_layout_item["layout"])

                if count > self.MAX_WIDGETS_PER_TAB:
                    self.errors.append(
                        ValidationError(
                            "TAB_WIDGET_LIMIT_EXCEEDED",
                            f"Tab '{tab_ref}' has {count} widgets (max {self.MAX_WIDGETS_PER_TAB})"
                        )
                    )

    def _find_layout_item(self, layout_items, ref_id):
        """Find a layout item by reference_id."""
        for item in layout_items:
            if item.get("reference_id") == ref_id:
                return item
            if "layout" in item:
                found = self._find_layout_item(item["layout"], ref_id)
                if found:
                    return found
        return None

    def _validate_hierarchy(self):
        """Validate hierarchy rules (tabs > sections > widgets)."""
        layout = self.dashboard.get("layout", [])
        widget_refs = {w.get("reference_id") for w in self.dashboard.get("widgets", [])}
        tab_refs = {t.get("reference_id") for t in self.dashboard.get("tabs", [])}
        section_refs = {s.get("reference_id") for s in self.dashboard.get("sections", [])}

        def validate_hierarchy_level(layout_items, parent_type="root"):
            for item in layout_items:
                ref_id = item.get("reference_id")

                # Determine item type
                if ref_id in tab_refs:
                    item_type = "tab"
                elif ref_id in section_refs:
                    item_type = "section"
                elif ref_id in widget_refs:
                    item_type = "widget"
                else:
                    item_type = "unknown"

                # Check hierarchy rules
                if parent_type == "root":
                    # Root can contain tabs, sections, or widgets
                    pass
                elif parent_type == "tab":
                    # Tabs can contain sections or widgets, not other tabs
                    if item_type == "tab":
                        self.errors.append(
                            ValidationError(
                                "INVALID_HIERARCHY",
                                f"Nested tabs not allowed: '{ref_id}' inside tab"
                            )
                        )
                elif parent_type == "section":
                    # Sections can only contain widgets
                    if item_type in ("tab", "section"):
                        self.errors.append(
                            ValidationError(
                                "INVALID_HIERARCHY",
                                f"Sections can only contain widgets, not {item_type}: '{ref_id}'"
                            )
                        )
                elif parent_type == "widget":
                    # Widgets cannot contain anything
                    self.errors.append(
                        ValidationError(
                            "INVALID_HIERARCHY",
                            f"Widgets cannot contain nested items: '{ref_id}'"
                        )
                    )

                # Recurse into nested layout
                if "layout" in item:
                    validate_hierarchy_level(item["layout"], item_type)

        validate_hierarchy_level(layout)

    def _validate_via_api(self):
        """Validate dashboard via DevRev API."""
        if not API_AVAILABLE:
            self.warnings.append(
                ValidationError(
                    "API_UNAVAILABLE",
                    "DevRev API client not available, skipping API validation",
                    severity="warning"
                )
            )
            return

        try:
            client = DevRevWidgetClient()
            result = client.validate_dashboard(self.dashboard)

            if not result.get("valid", False):
                errors = result.get("errors", [])
                for error in errors:
                    self.errors.append(
                        ValidationError(
                            "API_VALIDATION_ERROR",
                            error.get("message", "Unknown API error")
                        )
                    )
        except Exception as e:
            self.warnings.append(
                ValidationError(
                    "API_ERROR",
                    f"API validation failed: {str(e)}",
                    severity="warning"
                )
            )

    def get_report(self) -> str:
        """Generate validation report."""
        lines = []

        if self.errors:
            lines.append("VALIDATION FAILED\n")
            lines.append("Errors:")
            for error in self.errors:
                lines.append(f"  {error}")
        else:
            lines.append("VALIDATION PASSED\n")

        if self.warnings:
            lines.append("\nWarnings:")
            for warning in self.warnings:
                lines.append(f"  {warning}")

        return "\n".join(lines)


def main():
    """Main entry point."""
    if len(sys.argv) < 3:
        print("Usage: validate_dashboard.py <project_root> <dashboard_file> [--quiet] [--no-api] [--no-debug-log]")
        sys.exit(1)

    validation_start_time = time.time()

    project_root = Path(sys.argv[1])
    dashboard_file = Path(sys.argv[2])
    quiet = "--quiet" in sys.argv
    skip_api = "--no-api" in sys.argv
    no_debug_log = "--no-debug-log" in sys.argv

    workspace_dir = project_root.expanduser().resolve()

    # Make path absolute if relative
    if not dashboard_file.is_absolute():
        dashboard_file = project_root / dashboard_file

    # Initialize debug logger
    debug_logger = None
    if not no_debug_log and DebugLogger:
        try:
            debug_logger = DebugLogger(workspace_path=workspace_dir, enabled=True)
            # Use different log file for dashboard validation
            debug_logger.log_file = debug_logger.log_dir / "validation-dashboard.jsonl"
            debug_logger.log_validation_start(
                widget_path=str(dashboard_file.relative_to(workspace_dir)),
                mode="skip_api" if skip_api else "full_with_api"
            )
        except Exception as e:
            print(f"Warning: Failed to initialize debug logger: {e}", file=sys.stderr)

    # Check file exists
    if not dashboard_file.exists():
        print(f"Error: Dashboard file not found: {dashboard_file}")
        sys.exit(1)

    # Load JSON
    try:
        with open(dashboard_file, "r") as f:
            dashboard_data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: Could not read file: {e}")
        sys.exit(1)

    # Validate
    validator = DashboardValidator(dashboard_data, str(dashboard_file))
    passed = validator.validate(skip_api=skip_api)

    # Log results
    if debug_logger:
        try:
            # Create ValidationResult-like structure
            result_dict = {
                "valid": len(validator.errors) == 0,
                "errors": [{"rule_id": e.code, "message": e.message} for e in validator.errors],
                "warnings": [{"rule_id": w.code, "message": w.message} for w in validator.warnings]
            }
            from types import SimpleNamespace
            result = SimpleNamespace(**result_dict)

            debug_logger.log_stage_result("structure_and_api", result)
            debug_logger.log_validation_end(
                total_duration=time.time() - validation_start_time,
                final_result=len(validator.errors) == 0
            )
            debug_logger.rotate_logs()
        except Exception:
            pass  # Don't fail on logging errors

    # Report
    if not quiet:
        print(validator.get_report())

    # Exit code
    if passed:
        sys.exit(0)
    else:
        sys.exit(2)


if __name__ == "__main__":
    main()
