#!/usr/bin/env python3
"""
Validate dashboard.json for CREATE API format.

Checks for common errors:
1. Embedded widget objects (DOWNLOAD format) instead of ID-only references
2. Flat widget_id strings instead of nested widget objects
3. Missing required fields
4. Invalid hierarchy (widgets outside tabs)

Usage:
    python validate_dashboard_create_format.py <dashboard.json>
"""

import sys
import json
from pathlib import Path
from typing import Dict, Any, List, Tuple


class DashboardFormatValidator:
    def __init__(self):
        self.errors = []
        self.warnings = []

    def validate(self, dashboard_path: str) -> Tuple[bool, List[str], List[str]]:
        """
        Validate dashboard JSON for CREATE format.

        Returns:
            (is_valid, errors, warnings)
        """
        try:
            with open(dashboard_path, 'r') as f:
                dashboard = json.load(f)
        except FileNotFoundError:
            return False, [f"File not found: {dashboard_path}"], []
        except json.JSONDecodeError as e:
            return False, [f"Invalid JSON: {e}"], []

        # Check required fields
        self._check_required_fields(dashboard)

        # Check widget references
        self._check_widget_references(dashboard)

        # Check for forbidden fields
        self._check_forbidden_fields(dashboard)

        # Check hierarchy
        self._check_hierarchy(dashboard)

        is_valid = len(self.errors) == 0
        return is_valid, self.errors, self.warnings

    def _check_required_fields(self, dashboard: Dict[str, Any]):
        """Check for required top-level fields."""
        required = ['title', 'layout', 'tabs', 'widgets']
        for field in required:
            if field not in dashboard:
                self.errors.append(f"Missing required field: '{field}'")

    def _check_widget_references(self, dashboard: Dict[str, Any]):
        """
        Check widget array for proper CREATE format.

        CORRECT: {"reference_id": "w1", "widget": {"id": "don:..."}}
        WRONG: {"reference_id": "w1", "widget": {full object}}
        WRONG: {"reference_id": "w1", "widget_id": "don:..."}
        """
        widgets = dashboard.get('widgets', [])

        for idx, widget_ref in enumerate(widgets):
            ref_id = widget_ref.get('reference_id', f'<index {idx}>')

            # Check for flat widget_id (wrong format)
            if 'widget_id' in widget_ref:
                self.errors.append(
                    f"Widget '{ref_id}': Uses 'widget_id' field. "
                    f"API requires 'widget' object with 'id' key: "
                    f"{{'widget': {{'id': 'don:...'}}}}"
                )
                continue

            # Check for missing widget field
            if 'widget' not in widget_ref:
                self.errors.append(
                    f"Widget '{ref_id}': Missing 'widget' field"
                )
                continue

            widget = widget_ref['widget']

            # Check if widget is an object
            if not isinstance(widget, dict):
                self.errors.append(
                    f"Widget '{ref_id}': 'widget' must be an object with 'id' key"
                )
                continue

            # Check if widget has ONLY 'id' field (correct CREATE format)
            if 'id' not in widget:
                self.errors.append(
                    f"Widget '{ref_id}': 'widget' object missing 'id' field"
                )
                continue

            # Check for embedded widget fields (DOWNLOAD format)
            embedded_fields = [
                'title', 'data_sources', 'type', 'version',
                'created_by', 'created_date', 'modified_by', 'modified_date',
                'sub_widgets', 'layout', 'description'
            ]

            found_embedded = [f for f in embedded_fields if f in widget]
            if found_embedded:
                self.errors.append(
                    f"Widget '{ref_id}': Embedded widget object detected (DOWNLOAD format). "
                    f"Found fields: {', '.join(found_embedded)}. "
                    f"CREATE format requires ID-only reference: {{'widget': {{'id': '{widget.get('id', 'don:...')}'}}}}"
                )
                continue

            # Check for extra fields beyond 'id'
            extra_fields = [k for k in widget.keys() if k != 'id']
            if extra_fields:
                self.warnings.append(
                    f"Widget '{ref_id}': Unexpected fields in widget object: {', '.join(extra_fields)}. "
                    f"Only 'id' is required for CREATE format."
                )

            # Validate DON format
            widget_id = widget.get('id', '')
            if not widget_id.startswith('don:'):
                self.errors.append(
                    f"Widget '{ref_id}': Invalid widget ID format. "
                    f"Expected DON (don:data:...:widget/ID), got: {widget_id}"
                )

    def _check_forbidden_fields(self, dashboard: Dict[str, Any]):
        """Check for fields that API rejects in CREATE payloads."""
        # Root-level forbidden fields
        if 'version' in dashboard:
            self.errors.append(
                "Field 'version' not allowed at root level. API will reject this."
            )

        if 'description' in dashboard:
            self.warnings.append(
                "Root-level 'description' may be rejected. Move to tab descriptions."
            )

    def _check_hierarchy(self, dashboard: Dict[str, Any]):
        """Check that widgets are inside tabs, not at root."""
        layout = dashboard.get('layout', [])

        for item in layout:
            # Check if any layout item directly references a widget (wrong)
            ref_id = item.get('reference_id', '')
            if ref_id.startswith('widget'):
                self.errors.append(
                    f"Widget '{ref_id}' placed at root level. "
                    f"API requires: Dashboard → Tabs → (Sections) → Widgets"
                )


def main():
    if len(sys.argv) < 2:
        print("Usage: python validate_dashboard_create_format.py <dashboard.json>")
        sys.exit(1)

    dashboard_path = sys.argv[1]

    validator = DashboardFormatValidator()
    is_valid, errors, warnings = validator.validate(dashboard_path)

    # Print results
    print(f"\nValidating: {dashboard_path}")
    print("=" * 60)

    if warnings:
        print(f"\n⚠️  WARNINGS ({len(warnings)}):")
        for warning in warnings:
            print(f"  - {warning}")

    if errors:
        print(f"\n❌ ERRORS ({len(errors)}):")
        for error in errors:
            print(f"  - {error}")
        print("\n✗ Validation FAILED")
        print("\nCommon Fix: Remove embedded widget objects")
        print("  WRONG: {'widget': {'title': '...', 'data_sources': [...]}}")
        print("  RIGHT: {'widget': {'id': 'don:data:...:widget/W-123'}}")
        sys.exit(1)
    else:
        print("\n✓ Validation PASSED")
        print("\nDashboard format is correct for CREATE API.")
        sys.exit(0)


if __name__ == '__main__':
    main()
