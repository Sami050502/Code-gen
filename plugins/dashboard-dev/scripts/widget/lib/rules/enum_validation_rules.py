"""Enum value validation rules.

Validates that enum fields contain only permitted values from the Mosaic protobuf schema.
This prevents HTTP 406 errors caused by the protobuf validator rejecting invalid enum values.
"""

from typing import Dict, Any, List
from ..core.rule import ValidationRule
from ..core.models import ValidationError


# ============================================================================
# Enum Definitions (extracted from mosaic-client/api protobuf schema)
# ============================================================================

# MeerkatWidgetColumnFunction_TypeEnum
# Source: /Users/devrev/code/explorer/dashboard/mosaic-client/api/composite.pb.go
MEERKAT_FUNCTION_TYPES = {
    "MeerkatWidgetColumnFunction_TypeEnumSum",
    "MeerkatWidgetColumnFunction_TypeEnumAvg",
    "MeerkatWidgetColumnFunction_TypeEnumCount",
    "MeerkatWidgetColumnFunction_TypeEnumMin",
    "MeerkatWidgetColumnFunction_TypeEnumMax",
    "MeerkatWidgetColumnFunction_TypeEnumCountDistinct",
    "MeerkatWidgetColumnFunction_TypeEnumMedian",
    "MeerkatWidgetColumnFunction_TypeEnumP50",
    "MeerkatWidgetColumnFunction_TypeEnumP90",
    "MeerkatWidgetColumnFunction_TypeEnumP95",
    "MeerkatWidgetColumnFunction_TypeEnumP99",
    # Note: "Unknown" enum value (0) is excluded - never valid in actual use
}

# Common shorthand versions that agents might use
MEERKAT_FUNCTION_TYPE_SHORTCUTS = {
    "sum": "MeerkatWidgetColumnFunction_TypeEnumSum",
    "avg": "MeerkatWidgetColumnFunction_TypeEnumAvg",
    "count": "MeerkatWidgetColumnFunction_TypeEnumCount",
    "min": "MeerkatWidgetColumnFunction_TypeEnumMin",
    "max": "MeerkatWidgetColumnFunction_TypeEnumMax",
    "count_distinct": "MeerkatWidgetColumnFunction_TypeEnumCountDistinct",
    "median": "MeerkatWidgetColumnFunction_TypeEnumMedian",
    "p50": "MeerkatWidgetColumnFunction_TypeEnumP50",
    "p90": "MeerkatWidgetColumnFunction_TypeEnumP90",
    "p95": "MeerkatWidgetColumnFunction_TypeEnumP95",
    "p99": "MeerkatWidgetColumnFunction_TypeEnumP99",
}

# Widget_VersionEnum
# Source: /Users/devrev/code/explorer/dashboard/mosaic-client/api/schema.pb.go
WIDGET_VERSIONS = {
    "v0",  # Default version
    "v1",
    "v2",
}

# Visualization types (from widget analysis)
# Note: These are string keys in the visualization object, not protobuf enum
VISUALIZATION_TYPES = {
    "metric",
    "table",
    "bar",
    "line",
    "column",
    "area",
    "donut",
    "pie",
    "scatter",
    "combo",
    "gantt",
    "kanban",
    "rich_text",
}

# Valid meerkat_schema.type values
# Source: Gateway proto json_name values (composites.gen.proto:16015-16039)
# These are the ONLY values agents should use - simple and consistent with examples
MEERKAT_COLUMN_PROJECTION_TYPES = {
    "string",       # Text fields, IDs, enums
    "boolean",      # True/false flags
    "number",       # Integers, doubles, counts
    "time",         # Dates, timestamps
    "string_array", # Arrays of text/ID values
    "number_array", # Arrays of numeric values
}


# ============================================================================
# Validation Rules
# ============================================================================

class MeerkatFunctionTypeEnumRule(ValidationRule):
    """Validates that Meerkat function.type uses valid enum values.

    Common errors:
    - Using SQL function names (MEDIAN, PERCENTILE_CONT) instead of enum values
    - Using shorthand (p50) instead of full enum name
    - Typos in enum names
    """

    @property
    def rule_id(self) -> str:
        return "INVALID_MEERKAT_FUNCTION_TYPE_ENUM"

    @property
    def description(self) -> str:
        return "Meerkat function type must be a valid enum value"

    def validate(self, widget: Dict[str, Any]) -> List[ValidationError]:
        errors = []

        # Iterate through all data sources
        for ds_idx, data_source in enumerate(widget.get('data_sources', [])):
            # Check measures
            for m_idx, measure in enumerate(data_source.get('measures', [])):
                meerkat = measure.get('meerkat_schema', {})
                function = meerkat.get('function', {})

                if not function:
                    continue

                func_type = function.get('type')
                if not func_type:
                    continue

                # Check if valid enum value
                if func_type not in MEERKAT_FUNCTION_TYPES:
                    # Check if it's a shorthand that needs correction
                    suggestion = None
                    if func_type.lower() in MEERKAT_FUNCTION_TYPE_SHORTCUTS:
                        correct_value = MEERKAT_FUNCTION_TYPE_SHORTCUTS[func_type.lower()]
                        suggestion = f"Use full enum: function.type = '{correct_value}'"
                    else:
                        # Build helpful suggestion
                        valid_list = sorted(MEERKAT_FUNCTION_TYPES)
                        suggestion = f"Valid function types: {', '.join(valid_list)}"

                    errors.append(ValidationError(
                        rule_id=self.rule_id,
                        severity="error",
                        field_path=f"data_sources[{ds_idx}].measures[{m_idx}].meerkat_schema.function.type",
                        message=f"Invalid Meerkat function type: '{func_type}'",
                        suggestion=suggestion
                    ))

            # Check dimensions (in case they have functions)
            for d_idx, dimension in enumerate(data_source.get('dimensions', [])):
                meerkat = dimension.get('meerkat_schema', {})
                function = meerkat.get('function', {})

                if not function:
                    continue

                func_type = function.get('type')
                if not func_type:
                    continue

                if func_type not in MEERKAT_FUNCTION_TYPES:
                    suggestion = None
                    if func_type.lower() in MEERKAT_FUNCTION_TYPE_SHORTCUTS:
                        correct_value = MEERKAT_FUNCTION_TYPE_SHORTCUTS[func_type.lower()]
                        suggestion = f"Use full enum: function.type = '{correct_value}'"
                    else:
                        valid_list = sorted(MEERKAT_FUNCTION_TYPES)
                        suggestion = f"Valid function types: {', '.join(valid_list)}"

                    errors.append(ValidationError(
                        rule_id=self.rule_id,
                        severity="error",
                        field_path=f"data_sources[{ds_idx}].dimensions[{d_idx}].meerkat_schema.function.type",
                        message=f"Invalid Meerkat function type: '{func_type}'",
                        suggestion=suggestion
                    ))

        return errors


class WidgetVersionEnumRule(ValidationRule):
    """Validates that widget version is a valid enum value.

    Common errors:
    - Using numeric version (1, 2) instead of string ("v1", "v2")
    - Typos in version string
    """

    @property
    def rule_id(self) -> str:
        return "INVALID_WIDGET_VERSION"

    @property
    def description(self) -> str:
        return "Widget version must be a valid enum value (v0, v1, v2)"

    def validate(self, widget: Dict[str, Any]) -> List[ValidationError]:
        errors = []

        version = widget.get('version')
        if not version:
            # Version is optional, defaults to v0
            return errors

        # Normalize to lowercase for comparison
        version_str = str(version).lower()

        if version_str not in WIDGET_VERSIONS:
            errors.append(ValidationError(
                rule_id=self.rule_id,
                severity="error",
                field_path="version",
                message=f"Invalid widget version: '{version}'",
                suggestion=f"Valid versions: {', '.join(sorted(WIDGET_VERSIONS))}. Use string format (e.g., 'v0', not 0)"
            ))

        return errors


class VisualizationTypeValidationRule(ValidationRule):
    """Validates that visualization types are recognized.

    Note: This is informational - visualization types are validated by the API.
    But catching unknown types early helps agents avoid typos.
    """

    @property
    def rule_id(self) -> str:
        return "UNKNOWN_VISUALIZATION_TYPE"

    @property
    def description(self) -> str:
        return "Visualization type should be a recognized type"

    def validate(self, widget: Dict[str, Any]) -> List[ValidationError]:
        errors = []

        for sw_idx, sub_widget in enumerate(widget.get('sub_widgets', [])):
            viz = sub_widget.get('visualization', {})
            viz_type = viz.get('type')

            if not viz_type:
                # Type is required, but caught by structure validation
                continue

            if viz_type not in VISUALIZATION_TYPES:
                # This is a warning, not an error - API may support new types
                errors.append(ValidationError(
                    rule_id=self.rule_id,
                    severity="warning",
                    field_path=f"sub_widgets[{sw_idx}].visualization.type",
                    message=f"Unrecognized visualization type: '{viz_type}'",
                    suggestion=f"Common types: {', '.join(sorted(VISUALIZATION_TYPES))}"
                ))

        return errors


class MeerkatColumnProjectionTypeEnumRule(ValidationRule):
    """Validates that Meerkat column projection types use valid enum values.

    Common errors:
    - Using lowercase (number, text) instead of enum format
    - Using SQL types (INTEGER, VARCHAR) instead of Meerkat types
    """

    @property
    def rule_id(self) -> str:
        return "INVALID_MEERKAT_PROJECTION_TYPE"

    @property
    def description(self) -> str:
        return "Meerkat column projection type must be a valid enum value"

    def validate(self, widget: Dict[str, Any]) -> List[ValidationError]:
        errors = []

        for ds_idx, data_source in enumerate(widget.get('data_sources', [])):
            # Check measures
            for m_idx, measure in enumerate(data_source.get('measures', [])):
                meerkat = measure.get('meerkat_schema', {})
                proj_type = meerkat.get('type')

                if not proj_type:
                    continue

                if proj_type not in MEERKAT_COLUMN_PROJECTION_TYPES:
                    # Valid lowercase JSON values from Gateway proto
                    valid_lowercase = {"string", "boolean", "number", "time", "string_array", "number_array"}
                    suggestion = f"Valid types: {', '.join(sorted(valid_lowercase))}"

                    errors.append(ValidationError(
                        rule_id=self.rule_id,
                        severity="error",
                        field_path=f"data_sources[{ds_idx}].measures[{m_idx}].meerkat_schema.type",
                        message=f"Invalid Meerkat projection type: '{proj_type}'",
                        suggestion=suggestion
                    ))

            # Check dimensions
            for d_idx, dimension in enumerate(data_source.get('dimensions', [])):
                meerkat = dimension.get('meerkat_schema', {})
                proj_type = meerkat.get('type')

                if not proj_type:
                    continue

                if proj_type not in MEERKAT_COLUMN_PROJECTION_TYPES:
                    # Valid lowercase JSON values from Gateway proto
                    valid_lowercase = {"string", "boolean", "number", "time", "string_array", "number_array"}
                    suggestion = f"Valid types: {', '.join(sorted(valid_lowercase))}"

                    errors.append(ValidationError(
                        rule_id=self.rule_id,
                        severity="error",
                        field_path=f"data_sources[{ds_idx}].dimensions[{d_idx}].meerkat_schema.type",
                        message=f"Invalid Meerkat projection type: '{proj_type}'",
                        suggestion=suggestion
                    ))

        return errors
