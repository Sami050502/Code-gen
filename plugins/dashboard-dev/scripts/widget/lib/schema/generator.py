"""Validation generator from schema definitions."""

import re
from typing import Any, List, Callable, Dict

from ..core.models import ValidationError as VError
from .models import SchemaField, ObjectSchema, CompositeType
from .parser import MosaicSchemaParser


class ValidationGenerator:
    """
    Generates validation functions from schema definitions.
    """

    def __init__(self, parser: MosaicSchemaParser):
        """
        Initialize generator with parser.

        Args:
            parser: MosaicSchemaParser instance
        """
        self.parser = parser

    def generate_field_validator(
        self,
        field: SchemaField,
        field_path: str = ""
    ) -> Callable[[Any], List[VError]]:
        """
        Generate validator function for a field.

        Args:
            field: SchemaField to validate
            field_path: Path to field (for error messages)

        Returns:
            Validator function that returns list of validation errors
        """
        def validator(value: Any) -> List[VError]:
            errors = []

            # Check None/missing values
            if value is None:
                if field.is_required:
                    errors.append(VError(
                        rule_id="REQUIRED_FIELD",
                        severity="error",
                        field_path=field_path,
                        message=f"Required field '{field.name}' is missing",
                        suggestion=f"Add '{field.name}' field"
                    ))
                return errors

            # Array validation
            if field.is_array:
                if not isinstance(value, list):
                    errors.append(VError(
                        rule_id="INVALID_TYPE",
                        severity="error",
                        field_path=field_path,
                        message=f"Field '{field.name}' must be an array",
                        suggestion=f"Use array format for '{field.name}'"
                    ))
                    return errors

                # Validate array length
                if field.validation:
                    if field.validation.max_items is not None and len(value) > field.validation.max_items:
                        errors.append(VError(
                            rule_id="ARRAY_TOO_LONG",
                            severity="error",
                            field_path=field_path,
                            message=f"Array '{field.name}' exceeds max length {field.validation.max_items}",
                            suggestion=f"Reduce array size to {field.validation.max_items} items or fewer"
                        ))
                    if field.validation.min_items is not None and len(value) < field.validation.min_items:
                        errors.append(VError(
                            rule_id="ARRAY_TOO_SHORT",
                            severity="error",
                            field_path=field_path,
                            message=f"Array '{field.name}' requires at least {field.validation.min_items} items",
                            suggestion=f"Add more items to '{field.name}'"
                        ))

                # Validate each item
                for i, item in enumerate(value):
                    item_errors = self._validate_value(
                        item,
                        field.field_type,
                        field.composite_type,
                        f"{field_path}[{i}]",
                        field.validation,
                        field.enum_values
                    )
                    errors.extend(item_errors)

                return errors

            # Single value validation
            errors.extend(self._validate_value(
                value,
                field.field_type,
                field.composite_type,
                field_path,
                field.validation,
                field.enum_values
            ))

            return errors

        return validator

    def _validate_value(
        self,
        value: Any,
        field_type: str,
        composite_type: str = None,
        field_path: str = "",
        validation: Any = None,
        enum_values: List[str] = None
    ) -> List[VError]:
        """Validate a single value."""
        errors = []

        # Type validation
        if field_type == 'text':
            if not isinstance(value, str):
                errors.append(VError(
                    rule_id="INVALID_TYPE",
                    severity="error",
                    field_path=field_path,
                    message=f"Field must be a string, got {type(value).__name__}",
                ))
                return errors

            # String validation
            if validation:
                if validation.max_len is not None and len(value) > validation.max_len:
                    errors.append(VError(
                        rule_id="STRING_TOO_LONG",
                        severity="error",
                        field_path=field_path,
                        message=f"String exceeds max length {validation.max_len}",
                        suggestion=f"Shorten to {validation.max_len} characters or fewer"
                    ))
                if validation.min_len is not None and len(value) < validation.min_len:
                    errors.append(VError(
                        rule_id="STRING_TOO_SHORT",
                        severity="error",
                        field_path=field_path,
                        message=f"String must be at least {validation.min_len} characters",
                    ))
                if validation.pattern and not re.match(validation.pattern, value):
                    errors.append(VError(
                        rule_id="PATTERN_MISMATCH",
                        severity="error",
                        field_path=field_path,
                        message=f"String does not match required pattern: {validation.pattern}",
                    ))

        elif field_type == 'bool':
            if not isinstance(value, bool):
                errors.append(VError(
                    rule_id="INVALID_TYPE",
                    severity="error",
                    field_path=field_path,
                    message=f"Field must be a boolean, got {type(value).__name__}",
                ))

        elif field_type == 'tokens':
            # Tokens can be any type (object, array, string, etc.)
            pass

        elif field_type == 'composite':
            if not isinstance(value, dict):
                errors.append(VError(
                    rule_id="INVALID_TYPE",
                    severity="error",
                    field_path=field_path,
                    message=f"Field must be an object, got {type(value).__name__}",
                ))
                return errors

            # Validate composite type
            if composite_type:
                try:
                    comp_type = self.parser.get_composite_type(composite_type)
                    errors.extend(self._validate_composite(value, comp_type, field_path))
                except KeyError:
                    errors.append(VError(
                        rule_id="UNKNOWN_COMPOSITE_TYPE",
                        severity="error",
                        field_path=field_path,
                        message=f"Unknown composite type: {composite_type}",
                    ))

        # Enum validation
        if enum_values and value not in enum_values:
            errors.append(VError(
                rule_id="INVALID_ENUM",
                severity="error",
                field_path=field_path,
                message=f"Invalid value '{value}'. Must be one of: {', '.join(enum_values)}",
                suggestion=f"Use one of: {', '.join(enum_values)}"
            ))

        return errors

    def _validate_composite(
        self,
        obj: Dict[str, Any],
        composite: CompositeType,
        base_path: str
    ) -> List[VError]:
        """Validate object against composite type."""
        errors = []

        # Validate each field
        for field_name, field in composite.fields.items():
            field_path = f"{base_path}.{field_name}" if base_path else field_name
            value = obj.get(field_name)

            field_validator = self.generate_field_validator(field, field_path)
            errors.extend(field_validator(value))

        return errors

    def generate_object_validator(
        self,
        object_name: str
    ) -> Callable[[Dict], List[VError]]:
        """
        Generate validator function for a top-level object.

        Args:
            object_name: Name of object schema (e.g., 'widget')

        Returns:
            Validator function that returns list of validation errors
        """
        try:
            obj_schema = self.parser.get_object_schema(object_name)
        except KeyError:
            raise ValueError(f"Unknown object schema: {object_name}")

        def validator(obj: Dict[str, Any]) -> List[VError]:
            errors = []

            if not isinstance(obj, dict):
                errors.append(VError(
                    rule_id="INVALID_TYPE",
                    severity="error",
                    field_path="",
                    message=f"Object must be a dictionary, got {type(obj).__name__}",
                ))
                return errors

            # Validate each field
            for field_name, field in obj_schema.fields.items():
                value = obj.get(field_name)
                field_validator = self.generate_field_validator(field, field_name)
                errors.extend(field_validator(value))

            return errors

        return validator
