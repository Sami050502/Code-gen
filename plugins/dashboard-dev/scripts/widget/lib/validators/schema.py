"""Structure validator using JSON structure definition."""

import yaml
from pathlib import Path
from typing import Dict, Any
from jsonschema import validate, ValidationError as JSONSchemaValidationError

from ..core.models import ValidationResult, ValidationError, Stage


class StructureValidator:
    """Validates widget JSON structure against structure definition."""
    
    def __init__(self, structure_path: str = None):
        """
        Initialize structure validator.
        
        Args:
            structure_path: Path to widget.structure.yml file.
                           If None, looks for it in scripts/widget/ directory.
        """
        if structure_path is None:
            # Default to widget.structure.yml in same directory as this script
            structure_path = Path(__file__).parent.parent.parent / "widget.structure.yml"
        
        self.structure_path = Path(structure_path)
        self.structure = self._load_structure()
    
    def _load_structure(self) -> Dict[str, Any]:
        """Load YAML structure definition file."""
        if not self.structure_path.exists():
            raise FileNotFoundError(f"Structure file not found: {self.structure_path}")
        
        with open(self.structure_path, 'r') as f:
            return yaml.safe_load(f)
    
    def validate(self, widget: Dict[str, Any]) -> ValidationResult:
        """
        Validate widget structure against structure definition.
        
        Args:
            widget: Widget JSON dictionary
            
        Returns:
            ValidationResult with structure validation results
        """
        try:
            validate(instance=widget, schema=self.structure)
            return ValidationResult(Stage.STRUCTURE, True, [], [])
        
        except JSONSchemaValidationError as e:
            # Build field path from error path
            field_path = ".".join(str(p) for p in e.path) if e.path else "root"
            
            error = ValidationError(
                rule_id="STRUCTURE_VALIDATION",
                severity="error",
                field_path=field_path,
                message=e.message,
                suggestion=None
            )
            
            return ValidationResult(Stage.STRUCTURE, False, [error], [])


# Keep old name as alias for backward compatibility during transition
SchemaValidator = StructureValidator
