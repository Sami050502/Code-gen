"""Mosaic schema parser for dynamic validation."""

import yaml
from pathlib import Path
from typing import Dict, Any, Optional

from .models import ObjectSchema, CompositeType, SchemaField


class MosaicSchemaParser:
    """
    Parses mosaic-client/gen/schema.yaml and provides access to object schemas
    and composite types.
    """

    def __init__(self, schema_path: Optional[Path] = None):
        """
        Initialize parser with schema file path.

        Args:
            schema_path: Path to schema.yaml. If None, uses default location.
        """
        if schema_path is None:
            # Default to mosaic-schema.yaml in scripts/widget/ directory
            schema_path = Path(__file__).parent.parent.parent / "mosaic-schema.yaml"

        self.schema_path = Path(schema_path)
        self._schema_data: Dict[str, Any] = {}
        self._objects: Dict[str, ObjectSchema] = {}
        self._composite_types: Dict[str, CompositeType] = {}
        self._loaded = False

    def _load_schema(self):
        """Load and parse schema file."""
        if self._loaded:
            return

        if not self.schema_path.exists():
            raise FileNotFoundError(f"Schema file not found: {self.schema_path}")

        with open(self.schema_path, 'r') as f:
            self._schema_data = yaml.safe_load(f)

        # Parse object schemas
        for obj_name, obj_data in self._schema_data.get('objects', {}).items():
            self._objects[obj_name] = ObjectSchema.from_dict(obj_name, obj_data)

        # Parse composite types
        for type_name, type_data in self._schema_data.get('composite_types', {}).items():
            self._composite_types[type_name] = CompositeType.from_dict(type_name, type_data)

        self._loaded = True

    def get_object_schema(self, name: str) -> ObjectSchema:
        """
        Get object schema by name.

        Args:
            name: Object schema name (e.g., 'widget', 'dashboard')

        Returns:
            ObjectSchema instance

        Raises:
            KeyError: If schema not found
        """
        self._load_schema()
        if name not in self._objects:
            raise KeyError(f"Object schema not found: {name}")
        return self._objects[name]

    def get_composite_type(self, name: str) -> CompositeType:
        """
        Get composite type by name.

        Args:
            name: Composite type name

        Returns:
            CompositeType instance

        Raises:
            KeyError: If composite type not found
        """
        self._load_schema()
        if name not in self._composite_types:
            raise KeyError(f"Composite type not found: {name}")
        return self._composite_types[name]

    def resolve_field_type(self, field: SchemaField) -> Dict[str, Any]:
        """
        Resolve field type to its full definition.
        For composite types, returns the composite type definition.

        Args:
            field: SchemaField to resolve

        Returns:
            Dictionary with type information
        """
        self._load_schema()

        if field.field_type == 'composite' and field.composite_type:
            composite = self.get_composite_type(field.composite_type)
            return {
                'type': 'composite',
                'composite_type': field.composite_type,
                'fields': {name: self.resolve_field_type(f) for name, f in composite.fields.items()}
            }

        return {
            'type': field.field_type,
            'is_array': field.is_array,
            'is_required': field.is_required,
            'validation': field.validation,
            'enum_values': field.enum_values,
        }

    def get_version(self) -> str:
        """
        Get schema version.

        Returns:
            Schema version string
        """
        self._load_schema()
        return self._schema_data.get('version', 'unknown')

    def get_all_object_names(self) -> list:
        """Get list of all object schema names."""
        self._load_schema()
        return list(self._objects.keys())

    def get_all_composite_type_names(self) -> list:
        """Get list of all composite type names."""
        self._load_schema()
        return list(self._composite_types.keys())

    def reload(self):
        """Reload schema from disk (for hot-reloading)."""
        self._loaded = False
        self._schema_data = {}
        self._objects = {}
        self._composite_types = {}
        self._load_schema()
