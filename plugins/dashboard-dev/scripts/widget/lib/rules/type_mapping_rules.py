"""Type mapping validation rules based on runtime backend enforcement.

Source: mosaic/internal/utils/constants.go (RequiredDevrevToMeerkatTypeMap)
Backend: mosaic/internal/service/widget_create.go (validateCreateWidgetColumnProjection)
"""

from typing import Dict, Any, List, Optional, Set
from pathlib import Path
from ..core.rule import ValidationRule
from ..core.models import ValidationError

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False


class TypeMappingValidationRule(ValidationRule):
    """Validate devrev_field_type to meerkat_type mappings.

    This validation ensures that devrev schema types map correctly to meerkat types
    according to the backend's RequiredDevrevToMeerkatTypeMap. This catches type
    mismatch errors before the API call.

    Source: mosaic/internal/utils/constants.go lines 10-35
    Backend enforcement: widget_create.go:validateCreateWidgetColumnProjection()
    Error code: codes.InvalidArgument (gRPC)
    """

    def __init__(self):
        """Initialize with type mapping schema."""
        self._schema = self._load_validation_schema()

        # Load type mappings from schema
        if self._schema:
            type_mappings = self._schema.get('type_mappings', {})
            devrev_to_meerkat = type_mappings.get('devrev_to_meerkat', {})

            # Build mapping dictionary
            self.DEVREV_TO_MEERKAT_MAP = {}
            for devrev_type, config in devrev_to_meerkat.items():
                if isinstance(config, dict):
                    self.DEVREV_TO_MEERKAT_MAP[devrev_type] = config.get('meerkat_type')
                else:
                    self.DEVREV_TO_MEERKAT_MAP[devrev_type] = config

            self.UNSUPPORTED_TYPES = set(type_mappings.get('unsupported_types', []))
            self.AGGREGATE_FUNCTIONS = type_mappings.get('aggregate_functions', {})
        else:
            # Fallback to hardcoded mappings from backend source
            # Source: mosaic/internal/service/widget_create.go:validateCreateWidgetColumnProjection
            # Maps devrev field_type to both simple and enum Meerkat types
            self.DEVREV_TO_MEERKAT_MAP = {
                # Primitive types
                'int': 'number',
                'double': 'number',
                'bool': 'boolean',
                'date': 'time',
                'timestamp': 'time',
                # Non-primitive types
                'id': 'text',  # IDs are text in Meerkat
                'tokens': 'text',
                'text': 'text',
                'enum': 'text',
                'uenum': 'number',
                'number': 'number',  # Direct mapping
                # Array types
                '[]int': 'array',
                '[]double': 'array',
                '[]id': 'array',
                '[]text': 'array',
                '[]tokens': 'array',
                '[]enum': 'array',
                '[]uenum': 'array',
            }

            self.UNSUPPORTED_TYPES = {
                'composite', '[]bool', '[]date', '[]timestamp'
            }

            self.AGGREGATE_FUNCTIONS = {
                'count': {'output_type': 'number', 'rule': 'always_number'},
                'count_distinct': {'output_type': 'number', 'rule': 'always_number'},
                'sum': {'output_type': 'number', 'rule': 'always_number'},
                'avg': {'output_type': 'number', 'rule': 'always_number'},
                'median': {'output_type': 'number', 'rule': 'always_number'},
                'min': {'output_type': 'preserve_input', 'rule': 'preserve_input_type'},
                'max': {'output_type': 'preserve_input', 'rule': 'preserve_input_type'},
            }

        # Map simple type names to full enum names for BACKWARD COMPATIBILITY ONLY
        # Used by _normalize_meerkat_type() to parse existing widgets that may use
        # full enum names. All new widgets should use simple lowercase names.
        # Agents should ALWAYS use: "number", "string", "time", "boolean", "string_array", "number_array"
        # Source: mosaic-client/api/composite.pb.go (MeerkatWidgetColumnProjection_TypeEnum)
        self._MEERKAT_ENUM_TO_SIMPLE = {
            'MeerkatWidgetColumnProjection_TypeEnumNumber': 'number',
            'MeerkatWidgetColumnProjection_TypeEnumText': 'text',
            'MeerkatWidgetColumnProjection_TypeEnumTime': 'time',
            'MeerkatWidgetColumnProjection_TypeEnumBoolean': 'boolean',
            'MeerkatWidgetColumnProjection_TypeEnumArray': 'array',
            'MeerkatWidgetColumnProjection_TypeEnumObject': 'object',
        }
        # Simple names for quick lookup
        self._MEERKAT_SIMPLE_TYPES = {'number', 'text', 'time', 'boolean', 'array', 'object', 'string', 'string_array', 'number_array'}

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
        return "TYPE_MAPPING_VALIDATION"

    @property
    def description(self) -> str:
        return "DevRev to Meerkat type mappings must match backend requirements"

    def validate(self, widget: Dict[str, Any]) -> List[ValidationError]:
        """Run all type mapping validations."""
        errors = []

        for ds_idx, data_source in enumerate(widget.get('data_sources', [])):
            # Validate measures
            for measure_idx, measure in enumerate(data_source.get('measures', [])):
                errors.extend(self._validate_column_projection(
                    measure,
                    f"data_sources[{ds_idx}].measures[{measure_idx}]",
                    is_measure=True
                ))

            # Validate dimensions
            for dim_idx, dimension in enumerate(data_source.get('dimensions', [])):
                errors.extend(self._validate_column_projection(
                    dimension,
                    f"data_sources[{ds_idx}].dimensions[{dim_idx}]",
                    is_measure=False
                ))

        return errors

    def _validate_column_projection(
        self,
        column: Dict[str, Any],
        field_path: str,
        is_measure: bool
    ) -> List[ValidationError]:
        """Validate a single column projection (measure or dimension)."""
        errors = []

        devrev_schema = column.get('devrev_schema', {})
        meerkat_schema = column.get('meerkat_schema', {})

        devrev_type = devrev_schema.get('type')
        meerkat_type = meerkat_schema.get('type')
        reference_name = column.get('reference_name', 'unknown')

        if not devrev_type or not meerkat_type:
            # Missing type information - skip validation (other rules will catch this)
            return errors

        # Check for aggregate function
        function = meerkat_schema.get('function', {})
        function_type = function.get('type') if isinstance(function, dict) else None

        if function_type:
            # Validate aggregate function output type
            errors.extend(self._validate_aggregate_function(
                devrev_type,
                meerkat_type,
                function_type,
                reference_name,
                field_path
            ))
        else:
            # Validate direct type mapping
            errors.extend(self._validate_direct_type_mapping(
                devrev_type,
                meerkat_type,
                reference_name,
                field_path
            ))

        return errors

    def _validate_direct_type_mapping(
        self,
        devrev_type: str,
        meerkat_type: str,
        reference_name: str,
        field_path: str
    ) -> List[ValidationError]:
        """Validate direct devrev to meerkat type mapping (no aggregate function)."""
        errors = []

        # Check if type is unsupported
        if devrev_type in self.UNSUPPORTED_TYPES:
            errors.append(ValidationError(
                rule_id="UNSUPPORTED_FIELD_TYPE",
                severity="error",
                field_path=f"{field_path}.devrev_schema.type",
                message=f"{reference_name}: devrev schema type '{devrev_type}' is not supported",
                suggestion=f"Use one of the supported types: {', '.join(sorted(self.DEVREV_TO_MEERKAT_MAP.keys()))}"
            ))
            return errors

        # Check if type mapping exists
        expected_meerkat_type = self.DEVREV_TO_MEERKAT_MAP.get(devrev_type)

        if expected_meerkat_type is None:
            errors.append(ValidationError(
                rule_id="UNKNOWN_DEVREV_TYPE",
                severity="error",
                field_path=f"{field_path}.devrev_schema.type",
                message=f"{reference_name}: devrev schema type '{devrev_type}' is not recognized",
                suggestion=f"Use one of the supported types: {', '.join(sorted(self.DEVREV_TO_MEERKAT_MAP.keys()))}"
            ))
            return errors

        # Normalize meerkat_type to simple name for comparison
        # Handle both simple names ("number") and full enum names ("MeerkatWidgetColumnProjection_TypeEnumNumber")
        normalized_meerkat_type = self._normalize_meerkat_type(meerkat_type)

        # Check if meerkat type matches expected type
        if normalized_meerkat_type != expected_meerkat_type:
            # Always suggest simple lowercase type names (not full enum names)
            errors.append(ValidationError(
                rule_id="TYPE_MAPPING_MISMATCH",
                severity="error",
                field_path=f"{field_path}.meerkat_schema.type",
                message=f"{reference_name}: devrev schema type '{devrev_type}' cannot be used with meerkat schema type '{meerkat_type}'",
                suggestion=(
                    f"Use meerkat type '{expected_meerkat_type}' for devrev type '{devrev_type}'. "
                    "See **widget-development** skill `references/validation-schema.yaml` → 'type_mappings'"
                )
            ))

        return errors

    def _normalize_meerkat_type(self, meerkat_type: str) -> str:
        """Normalize meerkat type to simple name for comparison.

        Handles both formats:
        - Simple: "number" → "number"
        - Enum: "MeerkatWidgetColumnProjection_TypeEnumNumber" → "number"
        """
        # Check if it's already a simple type
        if meerkat_type in self._MEERKAT_SIMPLE_TYPES:
            return meerkat_type

        # Lookup full enum name → simple name
        simple = self._MEERKAT_ENUM_TO_SIMPLE.get(meerkat_type)
        if simple:
            return simple

        # Not recognized - return as-is for error reporting
        return meerkat_type.lower()

    def _validate_aggregate_function(
        self,
        devrev_type: str,
        meerkat_type: str,
        function_type: str,
        reference_name: str,
        field_path: str
    ) -> List[ValidationError]:
        """Validate aggregate function output type.

        Source: mosaic/internal/utils/constants.go:GetAggregateFunctionOutputType()
        Rules:
        - COUNT/COUNT_DISTINCT/SUM/AVG/MEDIAN always return 'number'
        - MIN/MAX preserve the input type
        """
        errors = []

        # Normalize function type (remove enum prefix if present)
        func_name = function_type.lower()
        if 'count_distinct' in func_name or 'countdistinct' in func_name:
            func_key = 'count_distinct'
        elif 'count' in func_name:
            func_key = 'count'
        elif 'sum' in func_name:
            func_key = 'sum'
        elif 'avg' in func_name or 'average' in func_name:
            func_key = 'avg'
        elif 'median' in func_name:
            func_key = 'median'
        elif 'min' in func_name:
            func_key = 'min'
        elif 'max' in func_name:
            func_key = 'max'
        else:
            # Unknown aggregate function - skip validation
            return errors

        func_config = self.AGGREGATE_FUNCTIONS.get(func_key, {})
        expected_output = func_config.get('output_type')
        rule = func_config.get('rule')

        if not expected_output:
            return errors

        if rule == 'always_number':
            # Functions that always output 'number'
            normalized_type = self._normalize_meerkat_type(meerkat_type)
            if normalized_type != 'number':
                # Always suggest simple lowercase type names
                errors.append(ValidationError(
                    rule_id="AGGREGATE_OUTPUT_TYPE_MISMATCH",
                    severity="error",
                    field_path=f"{field_path}.meerkat_schema.type",
                    message=f"{reference_name}: aggregate function '{func_key}' must use meerkat type 'number', got '{meerkat_type}'",
                    suggestion=f"Change meerkat_schema.type to 'number' for {func_key} function"
                ))

        elif rule == 'preserve_input_type':
            # MIN/MAX preserve input type - validate input type mapping
            expected_meerkat_type = self.DEVREV_TO_MEERKAT_MAP.get(devrev_type)
            normalized_type = self._normalize_meerkat_type(meerkat_type)

            if expected_meerkat_type and normalized_type != expected_meerkat_type:
                # Always suggest simple lowercase type names
                errors.append(ValidationError(
                    rule_id="AGGREGATE_PRESERVED_TYPE_MISMATCH",
                    severity="error",
                    field_path=f"{field_path}.meerkat_schema.type",
                    message=f"{reference_name}: {func_key} function with devrev type '{devrev_type}' must use meerkat type '{expected_meerkat_type}', got '{meerkat_type}'",
                    suggestion=f"Change meerkat_schema.type to '{expected_meerkat_type}' (preserves input type '{devrev_type}')"
                ))

        return errors
