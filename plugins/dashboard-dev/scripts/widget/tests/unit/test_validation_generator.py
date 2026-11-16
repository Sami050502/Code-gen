"""Unit tests for ValidationGenerator."""

import pytest
import tempfile
import yaml
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from lib.schema.parser import MosaicSchemaParser
from lib.schema.generator import ValidationGenerator


@pytest.fixture
def parser():
    """Create a parser with test schema."""
    schema_content = {
        'version': '1.0.0',
        'objects': {
            'test_object': {
                'fields': {
                    'title': {
                        'type': 'text',
                        'required': True,
                        'max_len': 50,
                        'pattern': '^[A-Z].*',
                    },
                    'status': {
                        'type': 'text',
                        'enum': ['active', 'inactive'],
                    },
                    'count': {
                        'type': 'text',
                    },
                    'enabled': {
                        'type': 'bool',
                    },
                    'items': {
                        'type': '[]composite',
                        'composite_type': 'item',
                        'min_items': 1,
                        'max_items': 10,
                    }
                }
            }
        },
        'composite_types': {
            'item': {
                'fields': {
                    'name': {
                        'type': 'text',
                        'required': True,
                    },
                    'metadata': {
                        'type': 'tokens',
                    }
                }
            }
        }
    }

    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(schema_content, f)
        temp_path = Path(f.name)

    parser = MosaicSchemaParser(temp_path)
    yield parser

    # Cleanup
    temp_path.unlink()


def test_validate_required_field(parser):
    """Test validation of required fields."""
    generator = ValidationGenerator(parser)
    obj_schema = parser.get_object_schema('test_object')
    title_field = obj_schema.fields['title']

    validator = generator.generate_field_validator(title_field, 'title')

    # Missing value
    errors = validator(None)
    assert len(errors) == 1
    assert errors[0].rule_id == 'REQUIRED_FIELD'

    # Present value
    errors = validator('Test Title')
    assert len(errors) == 0


def test_validate_string_max_length(parser):
    """Test string max length validation."""
    generator = ValidationGenerator(parser)
    obj_schema = parser.get_object_schema('test_object')
    title_field = obj_schema.fields['title']

    validator = generator.generate_field_validator(title_field, 'title')

    # Too long
    errors = validator('A' * 100)
    assert len(errors) == 1
    assert errors[0].rule_id == 'STRING_TOO_LONG'

    # Valid length
    errors = validator('Test')
    assert len(errors) == 0


def test_validate_string_pattern(parser):
    """Test string pattern validation."""
    generator = ValidationGenerator(parser)
    obj_schema = parser.get_object_schema('test_object')
    title_field = obj_schema.fields['title']

    validator = generator.generate_field_validator(title_field, 'title')

    # Invalid pattern
    errors = validator('lowercase')
    assert len(errors) == 1
    assert errors[0].rule_id == 'PATTERN_MISMATCH'

    # Valid pattern
    errors = validator('Uppercase')
    assert len(errors) == 0


def test_validate_enum(parser):
    """Test enum validation."""
    generator = ValidationGenerator(parser)
    obj_schema = parser.get_object_schema('test_object')
    status_field = obj_schema.fields['status']

    validator = generator.generate_field_validator(status_field, 'status')

    # Invalid enum value
    errors = validator('pending')
    assert len(errors) == 1
    assert errors[0].rule_id == 'INVALID_ENUM'

    # Valid enum value
    errors = validator('active')
    assert len(errors) == 0


def test_validate_bool_type(parser):
    """Test boolean type validation."""
    generator = ValidationGenerator(parser)
    obj_schema = parser.get_object_schema('test_object')
    enabled_field = obj_schema.fields['enabled']

    validator = generator.generate_field_validator(enabled_field, 'enabled')

    # Invalid type
    errors = validator('true')
    assert len(errors) == 1
    assert errors[0].rule_id == 'INVALID_TYPE'

    # Valid bool
    errors = validator(True)
    assert len(errors) == 0


def test_validate_array_length(parser):
    """Test array length validation."""
    generator = ValidationGenerator(parser)
    obj_schema = parser.get_object_schema('test_object')
    items_field = obj_schema.fields['items']

    validator = generator.generate_field_validator(items_field, 'items')

    # Too few items
    errors = validator([])
    assert any(e.rule_id == 'ARRAY_TOO_SHORT' for e in errors)

    # Too many items
    errors = validator([{'name': f'item{i}'} for i in range(20)])
    assert any(e.rule_id == 'ARRAY_TOO_LONG' for e in errors)

    # Valid array
    errors = validator([{'name': 'item1'}])
    assert len(errors) == 0


def test_validate_composite_type(parser):
    """Test composite type validation."""
    generator = ValidationGenerator(parser)
    obj_schema = parser.get_object_schema('test_object')
    items_field = obj_schema.fields['items']

    validator = generator.generate_field_validator(items_field, 'items')

    # Missing required field in composite
    errors = validator([{'metadata': {}}])
    assert any('name' in e.message for e in errors)

    # Valid composite
    errors = validator([{'name': 'test', 'metadata': {}}])
    assert len(errors) == 0


def test_validate_object(parser):
    """Test complete object validation."""
    generator = ValidationGenerator(parser)
    validator = generator.generate_object_validator('test_object')

    # Invalid object
    obj = {
        'title': 'lowercase',  # Pattern mismatch
        'status': 'pending',  # Invalid enum
        'count': 123,  # Wrong type
        'enabled': 'yes',  # Wrong type
        'items': [],  # Too few items
    }

    errors = validator(obj)
    assert len(errors) > 0
    assert any(e.rule_id == 'PATTERN_MISMATCH' for e in errors)
    assert any(e.rule_id == 'INVALID_ENUM' for e in errors)
    assert any(e.rule_id == 'INVALID_TYPE' for e in errors)

    # Valid object
    obj = {
        'title': 'Test Title',
        'status': 'active',
        'count': '5',
        'enabled': True,
        'items': [{'name': 'test1'}],
    }

    errors = validator(obj)
    assert len(errors) == 0


def test_tokens_type_accepts_any(parser):
    """Test that tokens type accepts any value."""
    generator = ValidationGenerator(parser)
    comp_type = parser.get_composite_type('item')
    metadata_field = comp_type.fields['metadata']

    validator = generator.generate_field_validator(metadata_field, 'metadata')

    # All should pass
    assert len(validator({'key': 'value'})) == 0
    assert len(validator(['a', 'b'])) == 0
    assert len(validator('string')) == 0
    assert len(validator(123)) == 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
