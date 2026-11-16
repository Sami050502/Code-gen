"""Unit tests for MosaicSchemaParser."""

import pytest
import tempfile
import yaml
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from lib.schema.parser import MosaicSchemaParser
from lib.schema.models import ObjectSchema, CompositeType, SchemaField


@pytest.fixture
def sample_schema_file():
    """Create a temporary schema file for testing."""
    schema_content = {
        'version': '1.0.0',
        'objects': {
            'test_widget': {
                'description': 'Test widget',
                'fields': {
                    'title': {
                        'type': 'text',
                        'required': True,
                        'max_len': 100,
                    },
                    'items': {
                        'type': '[]composite',
                        'composite_type': 'test_item',
                        'required': True,
                    }
                }
            }
        },
        'composite_types': {
            'test_item': {
                'description': 'Test item',
                'fields': {
                    'name': {
                        'type': 'text',
                        'required': True,
                    },
                    'value': {
                        'type': 'text',
                        'enum': ['a', 'b', 'c'],
                    }
                }
            }
        }
    }

    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(schema_content, f)
        temp_path = Path(f.name)

    yield temp_path

    # Cleanup
    temp_path.unlink()


def test_parse_object_schema(sample_schema_file):
    """Test parsing object schemas."""
    parser = MosaicSchemaParser(sample_schema_file)

    obj_schema = parser.get_object_schema('test_widget')

    assert obj_schema.name == 'test_widget'
    assert obj_schema.description == 'Test widget'
    assert 'title' in obj_schema.fields
    assert 'items' in obj_schema.fields

    title_field = obj_schema.fields['title']
    assert title_field.field_type == 'text'
    assert title_field.is_required is True
    assert title_field.validation is not None
    assert title_field.validation.max_len == 100


def test_parse_composite_type(sample_schema_file):
    """Test parsing composite types."""
    parser = MosaicSchemaParser(sample_schema_file)

    comp_type = parser.get_composite_type('test_item')

    assert comp_type.name == 'test_item'
    assert comp_type.description == 'Test item'
    assert 'name' in comp_type.fields
    assert 'value' in comp_type.fields

    value_field = comp_type.fields['value']
    assert value_field.enum_values == ['a', 'b', 'c']


def test_resolve_field_type(sample_schema_file):
    """Test resolving composite field types."""
    parser = MosaicSchemaParser(sample_schema_file)

    obj_schema = parser.get_object_schema('test_widget')
    items_field = obj_schema.fields['items']

    resolved = parser.resolve_field_type(items_field)

    assert resolved['type'] == 'composite'
    assert resolved['composite_type'] == 'test_item'
    assert 'fields' in resolved
    assert 'name' in resolved['fields']


def test_get_version(sample_schema_file):
    """Test getting schema version."""
    parser = MosaicSchemaParser(sample_schema_file)

    version = parser.get_version()
    assert version == '1.0.0'


def test_get_all_object_names(sample_schema_file):
    """Test getting all object names."""
    parser = MosaicSchemaParser(sample_schema_file)

    names = parser.get_all_object_names()
    assert 'test_widget' in names


def test_get_all_composite_type_names(sample_schema_file):
    """Test getting all composite type names."""
    parser = MosaicSchemaParser(sample_schema_file)

    names = parser.get_all_composite_type_names()
    assert 'test_item' in names


def test_missing_object_schema(sample_schema_file):
    """Test error when object schema not found."""
    parser = MosaicSchemaParser(sample_schema_file)

    with pytest.raises(KeyError):
        parser.get_object_schema('nonexistent')


def test_missing_composite_type(sample_schema_file):
    """Test error when composite type not found."""
    parser = MosaicSchemaParser(sample_schema_file)

    with pytest.raises(KeyError):
        parser.get_composite_type('nonexistent')


def test_reload_schema(sample_schema_file):
    """Test reloading schema."""
    parser = MosaicSchemaParser(sample_schema_file)

    # Load once
    version1 = parser.get_version()

    # Modify schema file
    with open(sample_schema_file, 'r') as f:
        schema = yaml.safe_load(f)
    schema['version'] = '2.0.0'
    with open(sample_schema_file, 'w') as f:
        yaml.dump(schema, f)

    # Reload
    parser.reload()
    version2 = parser.get_version()

    assert version1 == '1.0.0'
    assert version2 == '2.0.0'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
