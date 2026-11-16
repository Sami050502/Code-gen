"""Dynamic validator using mosaic-client schema."""

from pathlib import Path
from typing import Dict, Any, Optional

from ..core.models import ValidationResult, Stage
from ..schema.cache import get_cached_parser
from ..schema.generator import ValidationGenerator


class DynamicValidator:
    """
    Validates widgets against mosaic-client schema dynamically.
    Replaces StructureValidator with schema-driven validation.
    """

    def __init__(
        self,
        schema_path: Optional[Path] = None,
        object_type: str = "widget"
    ):
        """
        Initialize dynamic validator.

        Args:
            schema_path: Path to schema.yaml. If None, uses default location.
            object_type: Type of object to validate (default: 'widget')
        """
        self.schema_path = schema_path
        self.object_type = object_type
        self._parser = None
        self._generator = None

    def _ensure_initialized(self):
        """Ensure parser and generator are initialized."""
        if self._parser is None:
            self._parser = get_cached_parser(self.schema_path)
            self._generator = ValidationGenerator(self._parser)

    def validate(self, obj: Dict[str, Any]) -> ValidationResult:
        """
        Validate object against mosaic-client schema.

        Args:
            obj: Object to validate (e.g., widget JSON)

        Returns:
            ValidationResult with validation errors/warnings
        """
        self._ensure_initialized()

        try:
            # Generate validator for object type
            validator = self._generator.generate_object_validator(self.object_type)

            # Run validation
            errors = validator(obj)

            # Separate errors and warnings
            validation_errors = [e for e in errors if e.severity == "error"]
            validation_warnings = [e for e in errors if e.severity == "warning"]

            # Validation passes if no errors
            valid = len(validation_errors) == 0

            return ValidationResult(
                stage=Stage.STRUCTURE,
                valid=valid,
                errors=validation_errors,
                warnings=validation_warnings
            )

        except Exception as e:
            # Handle any unexpected errors
            from ..core.models import ValidationError
            return ValidationResult(
                stage=Stage.STRUCTURE,
                valid=False,
                errors=[ValidationError(
                    rule_id="VALIDATION_ERROR",
                    severity="error",
                    field_path="",
                    message=f"Validation failed: {str(e)}",
                )],
                warnings=[]
            )

    def refresh_schema(self):
        """Reload schema from disk (detect updates)."""
        if self._parser:
            self._parser.reload()

    def get_schema_version(self) -> str:
        """Get current schema version."""
        self._ensure_initialized()
        return self._parser.get_version()
