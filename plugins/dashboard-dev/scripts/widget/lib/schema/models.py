"""Data models for schema representation."""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any


@dataclass
class FieldValidation:
    """Validation rules for a field."""
    max_len: Optional[int] = None
    min_len: Optional[int] = None
    max_items: Optional[int] = None
    min_items: Optional[int] = None
    pattern: Optional[str] = None
    format: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FieldValidation':
        """Create from dictionary."""
        return cls(
            max_len=data.get('max_len'),
            min_len=data.get('min_len'),
            max_items=data.get('max_items'),
            min_items=data.get('min_items'),
            pattern=data.get('pattern'),
            format=data.get('format'),
        )


@dataclass
class SchemaField:
    """Represents a field in a schema."""
    name: str
    field_type: str  # text, tokens, bool, composite, []composite
    composite_type: Optional[str] = None
    is_required: bool = False
    is_array: bool = False
    validation: Optional[FieldValidation] = None
    enum_values: Optional[List[str]] = None
    description: Optional[str] = None
    display_name: Optional[str] = None

    @classmethod
    def from_dict(cls, name: str, data: Dict[str, Any]) -> 'SchemaField':
        """Create from dictionary."""
        field_type = data.get('type', 'text')
        is_array = field_type.startswith('[]')
        if is_array:
            field_type = field_type[2:]  # Remove [] prefix

        composite_type = None
        if field_type == 'composite':
            composite_type = data.get('composite_type')

        validation = None
        if any(k in data for k in ['max_len', 'min_len', 'max_items', 'min_items', 'pattern', 'format']):
            validation = FieldValidation.from_dict(data)

        return cls(
            name=name,
            field_type=field_type,
            composite_type=composite_type,
            is_required=data.get('required', False),
            is_array=is_array,
            validation=validation,
            enum_values=data.get('enum'),
            description=data.get('description'),
            display_name=data.get('display_name'),
        )


@dataclass
class CompositeType:
    """Represents a composite type definition."""
    name: str
    fields: Dict[str, SchemaField] = field(default_factory=dict)
    description: Optional[str] = None

    @classmethod
    def from_dict(cls, name: str, data: Dict[str, Any]) -> 'CompositeType':
        """Create from dictionary."""
        fields = {}
        for field_name, field_data in data.get('fields', {}).items():
            fields[field_name] = SchemaField.from_dict(field_name, field_data)

        return cls(
            name=name,
            fields=fields,
            description=data.get('description'),
        )


@dataclass
class ObjectSchema:
    """Represents a top-level object schema (widget, dashboard, data_source)."""
    name: str
    fields: Dict[str, SchemaField] = field(default_factory=dict)
    description: Optional[str] = None
    version: Optional[str] = None

    @classmethod
    def from_dict(cls, name: str, data: Dict[str, Any]) -> 'ObjectSchema':
        """Create from dictionary."""
        fields = {}
        for field_name, field_data in data.get('fields', {}).items():
            fields[field_name] = SchemaField.from_dict(field_name, field_data)

        return cls(
            name=name,
            fields=fields,
            description=data.get('description'),
            version=data.get('version'),
        )
