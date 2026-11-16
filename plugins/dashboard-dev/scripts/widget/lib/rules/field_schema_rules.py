"""Field schema validation rules.

Catches common field schema mistakes before they reach the API.
"""

from typing import Dict, List, Any


def validate_field_schemas(widget: Dict[str, Any], spec: Dict[str, Any]) -> List[Dict[str, str]]:
    """Validate field schema structure against common mistakes.

    Returns list of validation issues.
    """
    issues = []

    devrev_schema = widget.get('devrev_schema', {})
    fields = devrev_schema.get('fields', [])

    for field in fields:
        ref_name = field.get('reference_name', 'unknown')
        devrev = field.get('devrev_schema', {})
        meerkat = field.get('meerkat_schema', {})

        # Check 1: display_name at field root level (should be in devrev_schema.ui)
        if 'display_name' in field:
            issues.append({
                'rule': 'FIELD_SCHEMA_DISPLAY_NAME_LOCATION',
                'severity': 'error',
                'message': f"Field '{ref_name}': 'display_name' should be inside devrev_schema.ui.display_name, not at field root level",
                'field': ref_name
            })

        # Check 2: type in devrev_schema (should be field_type)
        if 'type' in devrev and 'field_type' not in devrev:
            issues.append({
                'rule': 'FIELD_SCHEMA_TYPE_VS_FIELD_TYPE',
                'severity': 'error',
                'message': f"Field '{ref_name}': Use 'field_type' in devrev_schema, not 'type'",
                'field': ref_name
            })

        # Check 3: column in meerkat_schema (should be sql_expression)
        if 'column' in meerkat:
            issues.append({
                'rule': 'FIELD_SCHEMA_COLUMN_VS_SQL_EXPRESSION',
                'severity': 'error',
                'message': f"Field '{ref_name}': Use 'sql_expression' in meerkat_schema, not 'column'",
                'field': ref_name
            })

    # Check 4: direction enum values in order_by
    order_by = widget.get('data', {}).get('order_by', [])
    for order in order_by:
        direction = order.get('direction', '')
        if direction in ['desc', 'asc']:
            issues.append({
                'rule': 'FIELD_SCHEMA_DIRECTION_ENUM',
                'severity': 'error',
                'message': f"Invalid direction value '{direction}'. Use 'descending' or 'ascending', not SQL shorthand",
                'field': order.get('reference_name', 'unknown')
            })

    return issues


def validate_widget_field_type_consistency(widget: Dict[str, Any], spec: Dict[str, Any]) -> List[Dict[str, str]]:
    """Validate field_type is present and consistent.

    Returns list of validation issues.
    """
    issues = []

    devrev_schema = widget.get('devrev_schema', {})
    fields = devrev_schema.get('fields', [])

    for field in fields:
        ref_name = field.get('reference_name', 'unknown')
        devrev = field.get('devrev_schema', {})

        # Ensure field_type is present
        if 'field_type' not in devrev:
            issues.append({
                'rule': 'FIELD_SCHEMA_MISSING_FIELD_TYPE',
                'severity': 'error',
                'message': f"Field '{ref_name}': Missing required 'field_type' in devrev_schema",
                'field': ref_name
            })

        # Ensure is_filterable is present
        if 'is_filterable' not in devrev:
            issues.append({
                'rule': 'FIELD_SCHEMA_MISSING_IS_FILTERABLE',
                'severity': 'warning',
                'message': f"Field '{ref_name}': Missing 'is_filterable' in devrev_schema (should be true for dimensions, false for measures)",
                'field': ref_name
            })

    return issues


# Registry of all field schema validation functions
FIELD_SCHEMA_VALIDATORS = [
    validate_field_schemas,
    validate_widget_field_type_consistency,
]
