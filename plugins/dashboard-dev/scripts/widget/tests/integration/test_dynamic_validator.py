"""Integration tests for DynamicValidator."""

import pytest
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from lib.validators.dynamic import DynamicValidator
from lib.core.models import Stage


@pytest.fixture
def validator():
    """Create DynamicValidator with default schema."""
    # This will use the mosaic-schema.yaml in scripts/widget/
    return DynamicValidator(object_type="widget")


def test_validate_valid_widget(validator):
    """Test validation of a valid widget."""
    widget = {
        'title': 'Test Widget',
        'description': 'A test widget',
        'version': 'v0',
        'data_sources': [
            {
                'reference_name': 'main_data',
                'type': 'oasis',
                'oasis': {
                    'sql_query': 'SELECT * FROM table',
                    'datasets': ['dataset1']
                }
            }
        ],
        'sub_widgets': [
            {
                'reference_id': 'chart1',
                'visualization': {
                    'type': 'table'
                }
            }
        ],
        'layout': []
    }

    result = validator.validate(widget)

    assert result.stage == Stage.STRUCTURE
    assert result.valid is True
    assert len(result.errors) == 0


def test_missing_required_fields(validator):
    """Test validation with missing required fields."""
    widget = {
        'description': 'Missing title and version',
        'data_sources': [],
        'sub_widgets': [],
        'layout': []
    }

    result = validator.validate(widget)

    assert result.valid is False
    assert any('title' in e.message for e in result.errors)
    assert any('version' in e.message for e in result.errors)


def test_field_length_violations(validator):
    """Test validation with field length violations."""
    widget = {
        'title': 'A' * 300,  # Exceeds max_len
        'description': 'Test',
        'version': 'v0',
        'data_sources': [],
        'sub_widgets': [
            {
                'reference_id': 'chart1',
                'visualization': {
                    'type': 'table'
                }
            }
        ],
        'layout': []
    }

    result = validator.validate(widget)

    assert result.valid is False
    assert any('STRING_TOO_LONG' in e.rule_id for e in result.errors)


def test_enum_violations(validator):
    """Test validation with invalid enum values."""
    widget = {
        'title': 'Test',
        'description': 'Test',
        'version': 'v99',  # Invalid version
        'data_sources': [],
        'sub_widgets': [
            {
                'reference_id': 'chart1',
                'visualization': {
                    'type': 'unknown_viz'  # Invalid visualization type
                }
            }
        ],
        'layout': []
    }

    result = validator.validate(widget)

    assert result.valid is False
    assert any('INVALID_ENUM' in e.rule_id for e in result.errors)


def test_composite_type_validation(validator):
    """Test validation of composite types."""
    widget = {
        'title': 'Test',
        'description': 'Test',
        'version': 'v0',
        'data_sources': [
            {
                # Missing required reference_name
                'type': 'oasis',
            }
        ],
        'sub_widgets': [
            {
                # Missing required visualization
                'reference_id': 'chart1',
            }
        ],
        'layout': []
    }

    result = validator.validate(widget)

    assert result.valid is False
    assert any('reference_name' in e.message for e in result.errors)
    assert any('visualization' in e.message for e in result.errors)


def test_nested_composite_validation(validator):
    """Test validation of nested composite types."""
    widget = {
        'title': 'Test',
        'description': 'Test',
        'version': 'v0',
        'data_sources': [
            {
                'reference_name': 'data',
                'type': 'oasis',
                'oasis': {
                    # Missing required sql_query
                    'datasets': ['dataset1']
                }
            }
        ],
        'sub_widgets': [
            {
                'reference_id': 'chart1',
                'visualization': {
                    'type': 'table'
                }
            }
        ],
        'layout': []
    }

    result = validator.validate(widget)

    assert result.valid is False
    assert any('sql_query' in e.message for e in result.errors)


def test_array_validation(validator):
    """Test validation of array fields."""
    widget = {
        'title': 'Test',
        'description': 'Test',
        'version': 'v0',
        'data_sources': [],
        'sub_widgets': [],  # Should have at least 1 sub_widget
        'layout': []
    }

    result = validator.validate(widget)

    assert result.valid is False
    assert any('sub_widgets' in e.field_path for e in result.errors)


def test_pattern_validation(validator):
    """Test validation of pattern constraints."""
    widget = {
        'title': 'Test',
        'description': 'Test',
        'version': 'v0',
        'data_sources': [
            {
                'reference_name': '123invalid',  # Must start with letter
                'type': 'oasis',
                'oasis': {
                    'sql_query': 'SELECT 1',
                    'datasets': ['dataset1']
                }
            }
        ],
        'sub_widgets': [
            {
                'reference_id': 'chart1',
                'visualization': {
                    'type': 'table'
                }
            }
        ],
        'layout': []
    }

    result = validator.validate(widget)

    assert result.valid is False
    assert any('PATTERN_MISMATCH' in e.rule_id for e in result.errors)


def test_get_schema_version(validator):
    """Test getting schema version."""
    version = validator.get_schema_version()
    assert version is not None
    assert isinstance(version, str)


def test_refresh_schema(validator):
    """Test refreshing schema."""
    # Should not raise an error
    validator.refresh_schema()

    # Should still work after refresh
    widget = {
        'title': 'Test',
        'description': 'Test',
        'version': 'v0',
        'data_sources': [],
        'sub_widgets': [
            {
                'reference_id': 'chart1',
                'visualization': {
                    'type': 'table'
                }
            }
        ],
        'layout': []
    }

    result = validator.validate(widget)
    assert result.stage == Stage.STRUCTURE


def test_invalid_object_type():
    """Test validation with non-dict input."""
    validator = DynamicValidator(object_type="widget")

    result = validator.validate("not a dict")

    assert result.valid is False
    assert len(result.errors) > 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
