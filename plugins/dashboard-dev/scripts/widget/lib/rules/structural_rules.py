"""Structural validation rules based on Mosaic schema."""

import re
from typing import Dict, Any, List, Optional, Set
from pathlib import Path
from ..core.rule import ValidationRule
from ..core.models import ValidationError

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False


class StructuralValidationRule(ValidationRule):
    """Validate widget structure against Mosaic schema constraints.

    Validates:
    - Enum values (visualization types, data source types, sort directions, versions)
    - Required fields (title, sub_widgets, visualization, reference_id, etc.)
    - Type-field consistency (type=line requires line config)
    - Field constraints (max lengths, array sizes, numeric ranges)

    These validations catch 60-70% of API rejections locally.
    """

    def __init__(self):
        """Initialize with validation schema."""
        self._schema = self._load_validation_schema()

        # Load enums from schema (fallback to hardcoded if schema unavailable)
        if self._schema:
            enums = self._schema.get('enums', {})
            self.VALID_VISUALIZATION_TYPES = set(enums.get('visualization_types', []))
            self.VALID_DATA_SOURCE_TYPES = set(enums.get('data_source_types', []))
            self.VALID_SORT_DIRECTIONS = set(enums.get('sort_directions', []))
            self.VALID_VERSIONS = set(enums.get('widget_versions', []))
        else:
            # Fallback to hardcoded values if schema unavailable
            self.VALID_VISUALIZATION_TYPES = {
                'line', 'bar', 'column', 'donut', 'pie', 'table',
                'metric', 'scatter', 'heatmap', 'packed_bubble',
                'rich_text', 'kanban', 'combination', 'flame', 'gantt'
            }
            self.VALID_DATA_SOURCE_TYPES = {
                'oasis', 'data_source', 'external_data_source', 'api', 'data_view'
            }
            self.VALID_SORT_DIRECTIONS = {'ascending', 'descending'}
            self.VALID_VERSIONS = {'v0', 'v1', 'v2'}

    @staticmethod
    def _load_validation_schema() -> Optional[Dict[str, Any]]:
        """Load validation schema from validation-schema.yaml.

        Searches in order:
        1. skills/widget-development/references/validation-schema.yaml (shared reference)
        2. scripts/widget/validation-schema.yaml (legacy location)
        """
        if not YAML_AVAILABLE:
            return None

        current_file = Path(__file__)
        # scripts/widget/lib/rules/ -> plugin root
        plugin_root = current_file.parent.parent.parent.parent.parent

        # Try shared reference location first (preferred)
        schema_locations = [
            plugin_root / "skills" / "widget-development" / "references" / "validation-schema.yaml",
            current_file.parent.parent.parent / "validation-schema.yaml",  # legacy
        ]

        for schema_file in schema_locations:
            if schema_file.exists():
                try:
                    with open(schema_file) as f:
                        return yaml.safe_load(f)
                except Exception:
                    continue

        return None

    @property
    def rule_id(self) -> str:
        return "STRUCTURAL_VALIDATION"

    @property
    def description(self) -> str:
        return "Widget structure must conform to Mosaic schema constraints"

    def validate(self, widget: Dict[str, Any]) -> List[ValidationError]:
        """Run all structural validations."""
        errors = []

        errors.extend(self._validate_required_fields(widget))
        errors.extend(self._validate_enums(widget))
        errors.extend(self._validate_type_field_consistency(widget))
        errors.extend(self._validate_constraints(widget))
        errors.extend(self._validate_visualization_required_fields(widget))

        return errors

    def _validate_required_fields(self, widget: Dict[str, Any]) -> List[ValidationError]:
        """Validate required fields are present."""
        errors = []

        # Widget-level required fields
        if not widget.get('title'):
            errors.append(ValidationError(
                rule_id="MISSING_REQUIRED_FIELD",
                severity="error",
                field_path="title",
                message="Required field 'title' is missing",
                suggestion="Add title field"
            ))

        if not widget.get('sub_widgets'):
            errors.append(ValidationError(
                rule_id="MISSING_REQUIRED_FIELD",
                severity="error",
                field_path="sub_widgets",
                message="Required field 'sub_widgets' is missing",
                suggestion="Add at least one sub_widget"
            ))

        # Sub-widget required fields
        for sw_idx, sub_widget in enumerate(widget.get('sub_widgets', [])):
            if not sub_widget.get('reference_id'):
                errors.append(ValidationError(
                    rule_id="MISSING_REQUIRED_FIELD",
                    severity="error",
                    field_path=f"sub_widgets[{sw_idx}].reference_id",
                    message="Required field 'reference_id' is missing",
                    suggestion="Add unique reference_id"
                ))

            viz = sub_widget.get('visualization')
            if not viz:
                errors.append(ValidationError(
                    rule_id="MISSING_REQUIRED_FIELD",
                    severity="error",
                    field_path=f"sub_widgets[{sw_idx}].visualization",
                    message="Required field 'visualization' is missing",
                    suggestion="Add visualization configuration"
                ))
            elif not viz.get('type'):
                errors.append(ValidationError(
                    rule_id="MISSING_REQUIRED_FIELD",
                    severity="error",
                    field_path=f"sub_widgets[{sw_idx}].visualization.type",
                    message="Required field 'type' is missing",
                    suggestion="Specify visualization type (line, bar, table, etc.)"
                ))

        # Data source required fields (if data_sources exist)
        for ds_idx, data_source in enumerate(widget.get('data_sources', [])):
            if not data_source.get('reference_name'):
                errors.append(ValidationError(
                    rule_id="MISSING_REQUIRED_FIELD",
                    severity="error",
                    field_path=f"data_sources[{ds_idx}].reference_name",
                    message="Required field 'reference_name' is missing",
                    suggestion="Add reference_name for data source"
                ))

            if not data_source.get('type'):
                errors.append(ValidationError(
                    rule_id="MISSING_REQUIRED_FIELD",
                    severity="error",
                    field_path=f"data_sources[{ds_idx}].type",
                    message="Required field 'type' is missing",
                    suggestion="Specify data source type (oasis, data_source, etc.)"
                ))

        return errors

    def _validate_enums(self, widget: Dict[str, Any]) -> List[ValidationError]:
        """Validate enum field values."""
        errors = []

        # Validate widget version
        version = widget.get('version')
        if version and version not in self.VALID_VERSIONS:
            errors.append(ValidationError(
                rule_id="INVALID_ENUM_VALUE",
                severity="error",
                field_path="version",
                message=f"Invalid version '{version}'",
                suggestion=f"Use one of: {', '.join(sorted(self.VALID_VERSIONS))}"
            ))

        # Validate visualization types
        for sw_idx, sub_widget in enumerate(widget.get('sub_widgets', [])):
            viz = sub_widget.get('visualization', {})
            viz_type = viz.get('type')

            if viz_type and viz_type not in self.VALID_VISUALIZATION_TYPES:
                errors.append(ValidationError(
                    rule_id="INVALID_ENUM_VALUE",
                    severity="error",
                    field_path=f"sub_widgets[{sw_idx}].visualization.type",
                    message=f"Invalid visualization type '{viz_type}'",
                    suggestion=(
                        f"Use one of: {', '.join(sorted(self.VALID_VISUALIZATION_TYPES))}. "
                        "Note: 'bar' = horizontal bars, 'column' = vertical bars. "
                        "See the **widget-development** skill reference `references/visualization-patterns.md`"
                    )
                ))

        # Validate data source types
        for ds_idx, data_source in enumerate(widget.get('data_sources', [])):
            ds_type = data_source.get('type')
            if ds_type and ds_type not in self.VALID_DATA_SOURCE_TYPES:
                errors.append(ValidationError(
                    rule_id="INVALID_ENUM_VALUE",
                    severity="error",
                    field_path=f"data_sources[{ds_idx}].type",
                    message=f"Invalid data source type '{ds_type}'",
                    suggestion=f"Use one of: {', '.join(sorted(self.VALID_DATA_SOURCE_TYPES))}"
                ))

        # Validate order_by direction
        for sw_idx, sub_widget in enumerate(widget.get('sub_widgets', [])):
            query = sub_widget.get('query', {})
            for ob_idx, order_by in enumerate(query.get('order_by', [])):
                direction = order_by.get('direction')
                if direction and direction not in self.VALID_SORT_DIRECTIONS:
                    errors.append(ValidationError(
                        rule_id="INVALID_ENUM_VALUE",
                        severity="error",
                        field_path=f"sub_widgets[{sw_idx}].query.order_by[{ob_idx}].direction",
                        message=f"Invalid sort direction '{direction}'",
                        suggestion="Use 'ascending' or 'descending'"
                    ))

        return errors

    def _validate_type_field_consistency(self, widget: Dict[str, Any]) -> List[ValidationError]:
        """Validate type enum matches corresponding composite field."""
        errors = []

        # Validate visualization type has matching config
        for sw_idx, sub_widget in enumerate(widget.get('sub_widgets', [])):
            viz = sub_widget.get('visualization', {})
            viz_type = viz.get('type')

            if not viz_type:
                continue

            # Check if type-specific config exists
            if viz_type in self.VALID_VISUALIZATION_TYPES and viz_type not in viz:
                errors.append(ValidationError(
                    rule_id="MISSING_TYPE_CONFIG",
                    severity="error",
                    field_path=f"sub_widgets[{sw_idx}].visualization.{viz_type}",
                    message=f"visualization.type is '{viz_type}' but '{viz_type}' config missing",
                    suggestion=f"Add '{viz_type}' configuration object"
                ))

        # Validate data_source type has matching config
        for ds_idx, data_source in enumerate(widget.get('data_sources', [])):
            ds_type = data_source.get('type')

            if ds_type == 'oasis' and not data_source.get('oasis'):
                errors.append(ValidationError(
                    rule_id="MISSING_TYPE_CONFIG",
                    severity="error",
                    field_path=f"data_sources[{ds_idx}].oasis",
                    message="data_source.type is 'oasis' but 'oasis' config missing",
                    suggestion="Add 'oasis' configuration object"
                ))
            elif ds_type == 'data_source' and not data_source.get('data_source'):
                errors.append(ValidationError(
                    rule_id="MISSING_TYPE_CONFIG",
                    severity="error",
                    field_path=f"data_sources[{ds_idx}].data_source",
                    message="data_source.type is 'data_source' but 'data_source' field missing",
                    suggestion="Add 'data_source' ID field"
                ))

        return errors

    def _validate_constraints(self, widget: Dict[str, Any]) -> List[ValidationError]:
        """Validate field length and numeric constraints."""
        errors = []

        # Load constraints from schema (with fallback values)
        if self._schema:
            constraints = self._schema.get('constraints', {})
            widget_constraints = constraints.get('widget', {})
            query_constraints = constraints.get('query', {})

            title_max_len = widget_constraints.get('title', {}).get('max_len', 256)
            description_max_len = widget_constraints.get('description', {}).get('max_len', 2048)
            sub_widgets_max_items = widget_constraints.get('sub_widgets', {}).get('max_items', 10)
            limit_gte = query_constraints.get('limit', {}).get('gte', 0)
        else:
            # Fallback to hardcoded constraints
            title_max_len = 256
            description_max_len = 2048
            sub_widgets_max_items = 10
            limit_gte = 0

        # title max_len
        title = widget.get('title', '')
        if title and len(title) > title_max_len:
            errors.append(ValidationError(
                rule_id="FIELD_TOO_LONG",
                severity="error",
                field_path="title",
                message=f"title exceeds max length ({len(title)} > {title_max_len})",
                suggestion=f"Shorten title to {title_max_len} characters or less"
            ))

        # description max_len
        description = widget.get('description', '')
        if description and len(description) > description_max_len:
            errors.append(ValidationError(
                rule_id="FIELD_TOO_LONG",
                severity="error",
                field_path="description",
                message=f"description exceeds max length ({len(description)} > {description_max_len})",
                suggestion=f"Shorten description to {description_max_len} characters or less"
            ))

        # sub_widgets max_items
        sub_widgets = widget.get('sub_widgets', [])
        if len(sub_widgets) > sub_widgets_max_items:
            errors.append(ValidationError(
                rule_id="TOO_MANY_ITEMS",
                severity="error",
                field_path="sub_widgets",
                message=f"Too many sub_widgets ({len(sub_widgets)} > {sub_widgets_max_items})",
                suggestion=f"Reduce to {sub_widgets_max_items} or fewer sub_widgets"
            ))

        # query.limit gte
        for sw_idx, sub_widget in enumerate(widget.get('sub_widgets', [])):
            query = sub_widget.get('query', {})
            limit = query.get('limit')
            if limit is not None and limit < limit_gte:
                errors.append(ValidationError(
                    rule_id="INVALID_VALUE",
                    severity="error",
                    field_path=f"sub_widgets[{sw_idx}].query.limit",
                    message=f"limit must be >= {limit_gte}, got {limit}",
                    suggestion=f"Use limit value >= {limit_gte}"
                ))

        return errors

    def _validate_visualization_required_fields(self, widget: Dict[str, Any]) -> List[ValidationError]:
        """Validate visualization-specific required fields (x/y axes, columns, etc)."""
        errors = []

        # Load visualization requirements from schema
        viz_requirements = {}
        if self._schema:
            viz_requirements = self._schema.get('visualization_required_fields', {})

        # Fallback to hardcoded requirements if schema unavailable
        if not viz_requirements:
            viz_requirements = {
                'line': {'x': True, 'y': True},
                'bar': {'x': True, 'y': True},
                'column': {'x': True, 'y': True},
                'donut': {'x': True, 'y': True},
                'pie': {'x': True, 'y': True},
                'scatter': {'x': True, 'y': True},
                'heatmap': {'x': True, 'y': True},
                'table': {'columns': True},
                'metric': {'y': True},
                'kanban': {'card_attributes': True},
                'packed_bubble': {'y': True},
                'combination': {'series': True, 'x_axis': True, 'y_axis': True},
            }

        for sw_idx, sub_widget in enumerate(widget.get('sub_widgets', [])):
            viz = sub_widget.get('visualization', {})
            viz_type = viz.get('type')

            if not viz_type or viz_type not in viz_requirements:
                continue

            viz_config = viz.get(viz_type, {})
            required_fields = viz_requirements.get(viz_type, {})

            # Check each required field
            for field_name, field_spec in required_fields.items():
                # Handle both simple (bool) and detailed (dict) format
                if isinstance(field_spec, dict):
                    is_required = field_spec.get('required', False)
                    field_type = field_spec.get('type', 'unknown')
                else:
                    is_required = field_spec
                    field_type = 'unknown'

                if not is_required:
                    continue

                field_value = viz_config.get(field_name)

                # Check if field is missing or empty
                if field_value is None:
                    errors.append(ValidationError(
                        rule_id="MISSING_REQUIRED_FIELD",
                        severity="error",
                        field_path=f"sub_widgets[{sw_idx}].visualization.{viz_type}.{field_name}",
                        message=f"{viz_type} visualization requires '{field_name}' field",
                        suggestion=f"Add {field_name} configuration to {viz_type} visualization"
                    ))
                # Check if array fields are non-empty (when type is known)
                elif field_type == 'array' and isinstance(field_value, list) and len(field_value) == 0:
                    errors.append(ValidationError(
                        rule_id="EMPTY_REQUIRED_ARRAY",
                        severity="error",
                        field_path=f"sub_widgets[{sw_idx}].visualization.{viz_type}.{field_name}",
                        message=f"{viz_type} visualization '{field_name}' cannot be empty",
                        suggestion=f"Add at least one item to {field_name} array"
                    ))

        return errors


class WidgetReferenceNameRule(ValidationRule):
    """Detect and reject reference_name at widget root level."""

    @property
    def rule_id(self) -> str:
        return "WIDGET_REFERENCE_NAME_AT_ROOT"

    @property
    def description(self) -> str:
        return "Field 'reference_name' is not allowed at widget root level"

    def validate(self, widget: Dict[str, Any]) -> List[ValidationError]:
        """Check if reference_name appears at widget root."""
        errors = []

        if "reference_name" in widget:
            errors.append(ValidationError(
                rule_id=self.rule_id,
                severity="error",
                field_path="reference_name",
                message="Field 'reference_name' is not allowed at widget root level",
                suggestion=(
                    "The 'reference_name' field should only appear in:\n"
                    "  1. data_sources[].reference_name (to identify data source)\n"
                    "  2. dimensions[].reference_name (to identify dimension fields)\n"
                    "  3. measures[].reference_name (to identify measure fields)\n\n"
                    "Remove 'reference_name' from widget root."
                )
            ))

        return errors


class WidgetNameRequiredRule(ValidationRule):
    """Validate that widget has a 'name' field.

    DISABLED: This rule has been disabled because the 'name' field is OPTIONAL at widget root level.

    The API error "Missing required field: name" is misleading - it refers to devrev_schema.name
    in measures/dimensions, NOT the widget root-level 'name' field.

    Widget root-level 'name' is optional but if provided must be unique per organization.
    The required 'name' fields are in data_sources[].measures[].devrev_schema.name and
    data_sources[].dimensions[].devrev_schema.name (must equal reference_name).

    This rule is disabled to avoid confusion between three different 'name' fields:
    1. Widget root 'name' (optional, unique per org if provided)
    2. devrev_schema 'name' (REQUIRED, equals reference_name)
    3. Dashboard root 'name' (optional, not unique)
    """

    @property
    def rule_id(self) -> str:
        return "MISSING_NAME_FIELD"

    @property
    def description(self) -> str:
        return "Widget must have a 'name' field (DISABLED - API validates)"

    def validate(self, widget: Dict[str, Any]) -> List[ValidationError]:
        """Check if name field is present (DISABLED)."""
        # Rule disabled - API is authoritative for required fields
        return []


class ReferenceIdPatternRule(ValidationRule):
    """Validate reference_id matches required pattern.

    Pattern: ^[a-zA-Z][a-zA-Z0-9_]*$
    - Must start with a letter
    - Can contain letters, numbers, and underscores
    - No hyphens, dots, or other special characters
    """

    # Pattern from validation-schema.yaml
    REFERENCE_ID_PATTERN = re.compile(r'^[a-zA-Z][a-zA-Z0-9_]*$')

    @property
    def rule_id(self) -> str:
        return "INVALID_REFERENCE_ID_PATTERN"

    @property
    def description(self) -> str:
        return "reference_id must match pattern ^[a-zA-Z][a-zA-Z0-9_]*$"

    def validate(self, widget: Dict[str, Any]) -> List[ValidationError]:
        """Check reference_id patterns in sub_widgets and layout."""
        errors = []

        # Check sub_widgets reference_id
        for sw_idx, sub_widget in enumerate(widget.get('sub_widgets', [])):
            ref_id = sub_widget.get('reference_id')
            if ref_id and not self.REFERENCE_ID_PATTERN.match(ref_id):
                errors.append(ValidationError(
                    rule_id=self.rule_id,
                    severity="error",
                    field_path=f"sub_widgets[{sw_idx}].reference_id",
                    message=f"reference_id '{ref_id}' does not match required pattern",
                    suggestion=(
                        "reference_id must:\n"
                        "  - Start with a letter (a-z, A-Z)\n"
                        "  - Contain only letters, numbers, and underscores\n"
                        "  - NOT contain hyphens, dots, or spaces\n\n"
                        f"Examples: 'chart1', 'my_chart', 'ticketCount'\n"
                        f"Invalid: '1-chart', 'my-chart', 'chart.1'"
                    )
                ))

        # Check layout reference_id
        for layout_idx, layout_item in enumerate(widget.get('layout', [])):
            ref_id = layout_item.get('reference_id')
            if ref_id and not self.REFERENCE_ID_PATTERN.match(ref_id):
                errors.append(ValidationError(
                    rule_id=self.rule_id,
                    severity="error",
                    field_path=f"layout[{layout_idx}].reference_id",
                    message=f"reference_id '{ref_id}' does not match required pattern",
                    suggestion=(
                        "reference_id must:\n"
                        "  - Start with a letter (a-z, A-Z)\n"
                        "  - Contain only letters, numbers, and underscores\n"
                        "  - NOT contain hyphens, dots, or spaces"
                    )
                ))

        return errors


class InvalidFieldDetectionRule(ValidationRule):
    """Detect fields that don't exist in the API schema.

    Common invalid fields that agents might try to use:
    - 'unit' - Use devrev_schema.ui.format instead
    - 'sorts' - Use query.order_by instead
    - 'angle' - Use donut.y or pie.y instead
    """

    # Fields that don't exist at widget root level
    INVALID_ROOT_FIELDS = {
        'unit': "Use 'devrev_schema.ui.format' for number formatting",
        'sorts': "Use 'query.order_by' array for sorting",
        'angle': "Use 'donut.y' or 'pie.y' for slice values",
        'type': "Widget root does not have a 'type' field. Did you mean 'visualization.type'?",
        'suffix': "The 'suffix' field does not exist in the widget schema. For number formatting, use 'devrev_schema.ui.format'",
    }

    # Fields that don't exist in visualization config
    INVALID_VIZ_FIELDS = {
        'angle': "Use 'y' field for the measure (slice sizes)",
    }

    @property
    def rule_id(self) -> str:
        return "INVALID_FIELD"

    @property
    def description(self) -> str:
        return "Detects fields that don't exist in the API schema"

    def validate(self, widget: Dict[str, Any]) -> List[ValidationError]:
        """Check for invalid fields."""
        errors = []

        # Check root-level invalid fields
        for field, suggestion in self.INVALID_ROOT_FIELDS.items():
            if field in widget:
                errors.append(ValidationError(
                    rule_id=self.rule_id,
                    severity="error",
                    field_path=field,
                    message=f"Invalid field: '{field}' does not exist in widget schema",
                    suggestion=suggestion
                ))

        # Check sub_widget level invalid fields
        for sw_idx, sub_widget in enumerate(widget.get('sub_widgets', [])):
            # Check for 'sorts' in sub_widget
            if 'sorts' in sub_widget:
                errors.append(ValidationError(
                    rule_id=self.rule_id,
                    severity="error",
                    field_path=f"sub_widgets[{sw_idx}].sorts",
                    message="Invalid field: 'sorts' does not exist",
                    suggestion="Use 'query.order_by' array for sorting"
                ))

            # Check visualization for invalid fields
            viz = sub_widget.get('visualization', {})
            viz_type = viz.get('type', '')
            viz_config = viz.get(viz_type, {})

            for field, suggestion in self.INVALID_VIZ_FIELDS.items():
                if field in viz_config:
                    errors.append(ValidationError(
                        rule_id=self.rule_id,
                        severity="error",
                        field_path=f"sub_widgets[{sw_idx}].visualization.{viz_type}.{field}",
                        message=f"Invalid field: '{field}' does not exist in {viz_type} visualization",
                        suggestion=suggestion
                    ))

        # Check data_source level invalid fields
        for ds_idx, data_source in enumerate(widget.get('data_sources', [])):
            if 'unit' in data_source:
                errors.append(ValidationError(
                    rule_id=self.rule_id,
                    severity="error",
                    field_path=f"data_sources[{ds_idx}].unit",
                    message="Invalid field: 'unit' does not exist in data_source",
                    suggestion="Use 'devrev_schema.ui.format' for number formatting"
                ))

            # Check measures for 'unit' field
            for m_idx, measure in enumerate(data_source.get('measures', [])):
                if 'unit' in measure:
                    errors.append(ValidationError(
                        rule_id=self.rule_id,
                        severity="error",
                        field_path=f"data_sources[{ds_idx}].measures[{m_idx}].unit",
                        message="Invalid field: 'unit' does not exist in measure",
                        suggestion="Use 'devrev_schema.ui.format' for number formatting"
                    ))

        return errors


class LayoutRequiredRule(ValidationRule):
    """Validate that widget has a 'layout' field.

    The layout field is required for widgets to render correctly.
    """

    @property
    def rule_id(self) -> str:
        return "MISSING_LAYOUT_FIELD"

    @property
    def description(self) -> str:
        return "Widget must have a 'layout' field"

    def validate(self, widget: Dict[str, Any]) -> List[ValidationError]:
        """Check if layout field is present and valid."""
        errors = []

        layout = widget.get('layout')
        if layout is None:
            errors.append(ValidationError(
                rule_id=self.rule_id,
                severity="error",
                field_path="layout",
                message="Required field 'layout' is missing",
                suggestion=(
                    "Add a 'layout' array to define sub_widget positions. Example:\n"
                    '"layout": [{\n'
                    '  "reference_id": "chart1",\n'
                    '  "position": {"x": 0, "y": 0, "width": 6, "height": 3}\n'
                    '}]'
                )
            ))
        elif isinstance(layout, list) and len(layout) == 0:
            errors.append(ValidationError(
                rule_id=self.rule_id,
                severity="error",
                field_path="layout",
                message="'layout' array is empty",
                suggestion="Add at least one layout item for each sub_widget"
            ))

        return errors


class TypeCompatibilityRule(ValidationRule):
    """Validate devrev_schema.field_type is compatible with meerkat_schema.type.

    The API validates type compatibility at runtime. This rule catches
    incompatible type combinations early (e.g., text→time is invalid).

    Valid mappings:
    - text, enum, id, tokens → string
    - int, double → number
    - timestamp, date → time
    - bool → boolean
    - []id, []text, []enum → string_array
    - []int, []double → number_array
    - Aggregate functions (COUNT, SUM, AVG, etc.) always output → number
    """

    # Valid devrev_schema.field_type → meerkat_schema.type mappings
    TYPE_COMPATIBILITY = {
        'text': {'string'},
        'enum': {'string'},
        'id': {'string'},
        'tokens': {'string'},
        'int': {'number'},
        'double': {'number'},
        'number': {'number'},  # Sometimes used directly
        'timestamp': {'time'},
        'date': {'time'},
        'bool': {'boolean'},
        'boolean': {'boolean'},  # Sometimes used directly
        '[]id': {'string_array'},
        '[]text': {'string_array'},
        '[]enum': {'string_array'},
        '[]int': {'number_array'},
        '[]double': {'number_array'},
        'array': {'string_array', 'number_array'},  # Generic array
    }

    # Aggregate functions always output number type
    AGGREGATE_FUNCTIONS = {
        'MeerkatWidgetColumnFunction_TypeEnumCount',
        'MeerkatWidgetColumnFunction_TypeEnumSum',
        'MeerkatWidgetColumnFunction_TypeEnumAvg',
        'MeerkatWidgetColumnFunction_TypeEnumMin',
        'MeerkatWidgetColumnFunction_TypeEnumMax',
        'MeerkatWidgetColumnFunction_TypeEnumMedian',
        'MeerkatWidgetColumnFunction_TypeEnumP50',
        'MeerkatWidgetColumnFunction_TypeEnumP90',
        'MeerkatWidgetColumnFunction_TypeEnumP95',
        'MeerkatWidgetColumnFunction_TypeEnumP99',
    }

    @property
    def rule_id(self) -> str:
        return "TYPE_COMPATIBILITY_ERROR"

    @property
    def description(self) -> str:
        return "devrev_schema.field_type must be compatible with meerkat_schema.type"

    def validate(self, widget: Dict[str, Any]) -> List[ValidationError]:
        """Check type compatibility in all dimensions and measures."""
        errors = []

        for ds_idx, data_source in enumerate(widget.get('data_sources', [])):
            # Check dimensions
            for dim_idx, dim in enumerate(data_source.get('dimensions', [])):
                error = self._check_field_compatibility(
                    dim,
                    f"data_sources[{ds_idx}].dimensions[{dim_idx}]"
                )
                if error:
                    errors.append(error)

            # Check measures
            for m_idx, measure in enumerate(data_source.get('measures', [])):
                error = self._check_field_compatibility(
                    measure,
                    f"data_sources[{ds_idx}].measures[{m_idx}]"
                )
                if error:
                    errors.append(error)

        return errors

    def _check_field_compatibility(
        self,
        field: Dict[str, Any],
        field_path: str
    ) -> Optional[ValidationError]:
        """Check if a single field has compatible types."""
        devrev_schema = field.get('devrev_schema', {})
        meerkat_schema = field.get('meerkat_schema', {})

        devrev_type = devrev_schema.get('field_type')
        meerkat_type = meerkat_schema.get('type')

        # Skip if either type is missing (other rules handle that)
        if not devrev_type or not meerkat_type:
            return None

        # Check if using aggregate function (always outputs number)
        function = meerkat_schema.get('function', {})
        function_type = function.get('type', '')
        if function_type in self.AGGREGATE_FUNCTIONS:
            if meerkat_type != 'number':
                return ValidationError(
                    rule_id=self.rule_id,
                    severity="error",
                    field_path=f"{field_path}.meerkat_schema.type",
                    message=f"Aggregate function '{function_type}' requires meerkat_schema.type='number', got '{meerkat_type}'",
                    suggestion="Change meerkat_schema.type to 'number' (aggregate functions always output numbers)"
                )
            return None  # Valid aggregate function

        # Check type compatibility
        valid_meerkat_types = self.TYPE_COMPATIBILITY.get(devrev_type)
        if valid_meerkat_types is None:
            # Unknown devrev type - skip validation
            return None

        if meerkat_type not in valid_meerkat_types:
            valid_types_str = ', '.join(sorted(valid_meerkat_types))
            return ValidationError(
                rule_id=self.rule_id,
                severity="error",
                field_path=f"{field_path}",
                message=f"devrev_schema.field_type='{devrev_type}' is incompatible with meerkat_schema.type='{meerkat_type}'",
                suggestion=f"For field_type='{devrev_type}', use meerkat_schema.type: {valid_types_str}"
            )

        return None


class SqlExpressionRequiredRule(ValidationRule):
    """Validate that measures have non-empty sql_expression.

    API rejects measures with missing or empty sql_expression:
    "Bad Request: Missing required field: sql_expression"

    This catches the error before API validation.
    """

    @property
    def rule_id(self) -> str:
        return "MISSING_SQL_EXPRESSION"

    @property
    def description(self) -> str:
        return "Measures must have a non-empty sql_expression in meerkat_schema"

    def validate(self, widget: Dict[str, Any]) -> List[ValidationError]:
        """Check that all measures have sql_expression."""
        errors = []

        for ds_idx, data_source in enumerate(widget.get('data_sources', [])):
            for m_idx, measure in enumerate(data_source.get('measures', [])):
                meerkat_schema = measure.get('meerkat_schema', {})
                sql_expression = meerkat_schema.get('sql_expression')

                # Check for missing sql_expression
                if sql_expression is None:
                    ref_name = measure.get('reference_name', f'measures[{m_idx}]')
                    errors.append(ValidationError(
                        rule_id=self.rule_id,
                        severity="error",
                        field_path=f"data_sources[{ds_idx}].measures[{m_idx}].meerkat_schema.sql_expression",
                        message=f"Measure '{ref_name}' is missing required 'sql_expression' in meerkat_schema",
                        suggestion=(
                            "Add sql_expression to the measure's meerkat_schema:\n\n"
                            "For simple column reference:\n"
                            "  \"meerkat_schema\": {\n"
                            "    \"sql_expression\": \"column_name\",\n"
                            "    \"type\": \"number\"\n"
                            "  }\n\n"
                            "For aggregate expression:\n"
                            "  \"meerkat_schema\": {\n"
                            "    \"sql_expression\": \"SUM(column_name)\",\n"
                            "    \"type\": \"number\"\n"
                            "  }"
                        )
                    ))
                # Check for empty sql_expression
                elif isinstance(sql_expression, str) and sql_expression.strip() == '':
                    ref_name = measure.get('reference_name', f'measures[{m_idx}]')
                    errors.append(ValidationError(
                        rule_id=self.rule_id,
                        severity="error",
                        field_path=f"data_sources[{ds_idx}].measures[{m_idx}].meerkat_schema.sql_expression",
                        message=f"Measure '{ref_name}' has empty 'sql_expression'",
                        suggestion=(
                            "sql_expression cannot be empty. Add a valid expression:\n\n"
                            "For simple column: \"column_name\"\n"
                            "For aggregate: \"SUM(column_name)\", \"COUNT(*)\", \"AVG(value)\""
                        )
                    ))

        return errors


class InvalidFunctionLocationRule(ValidationRule):
    """Detect `function` field at invalid locations.

    The `function` field is only valid inside `meerkat_schema.function`.
    Common mistakes:
    - `function` at widget root level
    - `function` inside `devrev_schema` (should be in meerkat_schema)
    - `function` at measure/dimension root level

    These placements cause API rejection with "Invalid field: function".
    """

    @property
    def rule_id(self) -> str:
        return "INVALID_FUNCTION_LOCATION"

    @property
    def description(self) -> str:
        return "Field 'function' must only appear in meerkat_schema.function"

    def validate(self, widget: Dict[str, Any]) -> List[ValidationError]:
        """Check for function field at invalid locations."""
        errors = []

        # Check widget root level
        if 'function' in widget:
            errors.append(ValidationError(
                rule_id=self.rule_id,
                severity="error",
                field_path="function",
                message="Invalid field: 'function' is not allowed at widget root level",
                suggestion=(
                    "The 'function' field should only appear inside meerkat_schema:\n\n"
                    "CORRECT:\n"
                    "  \"meerkat_schema\": {\n"
                    "    \"type\": \"number\",\n"
                    "    \"function\": {\n"
                    "      \"type\": \"MeerkatWidgetColumnFunction_TypeEnumP50\"\n"
                    "    },\n"
                    "    \"sql_expression\": \"column_name\"\n"
                    "  }\n\n"
                    "WRONG:\n"
                    "  \"function\": {...}  // at widget root\n\n"
                    "Remove 'function' from widget root and place it inside meerkat_schema."
                )
            ))

        # Check data_sources for invalid function placement
        for ds_idx, data_source in enumerate(widget.get('data_sources', [])):
            # Check measures
            for m_idx, measure in enumerate(data_source.get('measures', [])):
                # Check for function at measure root
                if 'function' in measure:
                    errors.append(ValidationError(
                        rule_id=self.rule_id,
                        severity="error",
                        field_path=f"data_sources[{ds_idx}].measures[{m_idx}].function",
                        message="Invalid field: 'function' is not allowed at measure root level",
                        suggestion=(
                            "Move 'function' inside meerkat_schema:\n\n"
                            "CORRECT:\n"
                            "  \"measures\": [{\n"
                            "    \"meerkat_schema\": {\n"
                            "      \"function\": {\"type\": \"MeerkatWidgetColumnFunction_TypeEnumP50\"},\n"
                            "      ...\n"
                            "    }\n"
                            "  }]\n\n"
                            "WRONG:\n"
                            "  \"measures\": [{\n"
                            "    \"function\": {...},  // Should not be here\n"
                            "    \"meerkat_schema\": {...}\n"
                            "  }]"
                        )
                    ))

                # Check for function inside devrev_schema
                devrev_schema = measure.get('devrev_schema', {})
                if 'function' in devrev_schema:
                    errors.append(ValidationError(
                        rule_id=self.rule_id,
                        severity="error",
                        field_path=f"data_sources[{ds_idx}].measures[{m_idx}].devrev_schema.function",
                        message="Invalid field: 'function' is not allowed in devrev_schema",
                        suggestion=(
                            "Move 'function' to meerkat_schema instead:\n\n"
                            "CORRECT:\n"
                            "  \"meerkat_schema\": {\n"
                            "    \"function\": {\"type\": \"MeerkatWidgetColumnFunction_TypeEnumP50\"}\n"
                            "  }\n\n"
                            "WRONG:\n"
                            "  \"devrev_schema\": {\n"
                            "    \"function\": {...}  // Should not be here\n"
                            "  }"
                        )
                    ))

            # Check dimensions
            for d_idx, dimension in enumerate(data_source.get('dimensions', [])):
                # Check for function at dimension root
                if 'function' in dimension:
                    errors.append(ValidationError(
                        rule_id=self.rule_id,
                        severity="error",
                        field_path=f"data_sources[{ds_idx}].dimensions[{d_idx}].function",
                        message="Invalid field: 'function' is not allowed at dimension root level",
                        suggestion="Dimensions typically don't use function. If needed, place inside meerkat_schema."
                    ))

                # Check for function inside devrev_schema
                devrev_schema = dimension.get('devrev_schema', {})
                if 'function' in devrev_schema:
                    errors.append(ValidationError(
                        rule_id=self.rule_id,
                        severity="error",
                        field_path=f"data_sources[{ds_idx}].dimensions[{d_idx}].devrev_schema.function",
                        message="Invalid field: 'function' is not allowed in devrev_schema",
                        suggestion="Move 'function' to meerkat_schema if needed."
                    ))

        return errors


class WrappedFormatDetectionRule(ValidationRule):
    """Detect widgets in DOWNLOAD format (wrapped in outer object).

    Downloaded widgets have an outer wrapper with platform fields:
    {
      "widget": {
        "id": "don:...",
        "title": "...",
        "created_by": {...},
        ...
      }
    }

    CREATE format widgets should have title, data_sources, etc. at root level.
    This catches the common mistake of using downloaded JSON directly.
    """

    # Fields that indicate DOWNLOAD format (outer wrapper present)
    WRAPPER_INDICATORS = {'widget'}

    # Platform-only fields that appear in DOWNLOAD format
    PLATFORM_FIELDS = {
        'id', 'display_id', 'created_by', 'created_date',
        'modified_by', 'modified_date', 'object_version', 'stock'
    }

    @property
    def rule_id(self) -> str:
        return "DOWNLOAD_FORMAT_DETECTED"

    @property
    def description(self) -> str:
        return "Widget appears to be in DOWNLOAD format instead of CREATE format"

    def validate(self, widget: Dict[str, Any]) -> List[ValidationError]:
        """Check if widget is in DOWNLOAD format."""
        errors = []

        # Check for outer wrapper
        if 'widget' in widget and isinstance(widget.get('widget'), dict):
            inner = widget['widget']
            # Check if inner object has widget content fields
            widget_content_fields = {'title', 'data_sources', 'sub_widgets', 'version'}
            if any(f in inner for f in widget_content_fields):
                errors.append(ValidationError(
                    rule_id=self.rule_id,
                    severity="error",
                    field_path="widget",
                    message="Widget is in DOWNLOAD format (wrapped in outer 'widget' object)",
                    suggestion=(
                        "Convert to CREATE format by removing the outer wrapper.\n\n"
                        "DOWNLOAD format (current):\n"
                        '  {"widget": {"title": "...", "data_sources": [...]}}\n\n'
                        "CREATE format (required):\n"
                        '  {"title": "...", "data_sources": [...]}\n\n'
                        "Extract the contents of the 'widget' key to the root level."
                    )
                ))
                return errors

        # Check for platform-only fields at root (also indicates downloaded data)
        found_platform_fields = [f for f in self.PLATFORM_FIELDS if f in widget]
        if found_platform_fields and 'title' in widget:
            # This is a widget with platform fields at root - likely downloaded
            # and unwrapped but not cleaned
            errors.append(ValidationError(
                rule_id="PLATFORM_FIELDS_DETECTED",
                severity="warning",
                field_path="",
                message=f"Widget contains platform-only fields: {', '.join(found_platform_fields)}",
                suggestion=(
                    "These fields are added by the platform and should be removed "
                    "before creating/updating widgets. Use the CLI's normalize function "
                    "or manually remove: id, display_id, created_by, created_date, "
                    "modified_by, modified_date, object_version, stock"
                )
            ))

        return errors
