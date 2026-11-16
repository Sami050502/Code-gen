"""Tests for enum validation rules."""

import pytest
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from lib.rules.enum_validation_rules import (
    MeerkatColumnProjectionTypeEnumRule,
    MEERKAT_COLUMN_PROJECTION_TYPES,
)


class TestMeerkatColumnProjectionTypes:
    """Tests for MEERKAT_COLUMN_PROJECTION_TYPES set."""

    def test_valid_types_in_set(self):
        """All valid types should be in the set."""
        valid_types = ["string", "boolean", "number", "time", "string_array", "number_array"]
        for t in valid_types:
            assert t in MEERKAT_COLUMN_PROJECTION_TYPES, f"'{t}' should be valid"

    def test_only_six_valid_types(self):
        """Set should contain exactly 6 valid types."""
        assert len(MEERKAT_COLUMN_PROJECTION_TYPES) == 6

    def test_invalid_types_not_in_set(self):
        """Invalid types should NOT be in the set."""
        invalid_types = [
            "text",      # Wrong - use "string"
            "array",     # Wrong - use "string_array" or "number_array"
            "object",    # Not supported
            "int",       # SQL type, not meerkat type
            "varchar",   # SQL type, not meerkat type
            "timestamp", # Use "time" instead
            # Full enum names should NOT be in set (unnecessary complexity)
            "MeerkatWidgetColumnProjection_TypeEnumString",
            "MeerkatWidgetColumnProjection_TypeEnumNumber",
        ]
        for t in invalid_types:
            assert t not in MEERKAT_COLUMN_PROJECTION_TYPES, f"'{t}' should NOT be valid"


class TestMeerkatColumnProjectionTypeEnumRule:
    """Tests for MeerkatColumnProjectionTypeEnumRule."""

    def setup_method(self):
        self.rule = MeerkatColumnProjectionTypeEnumRule()

    def test_all_valid_types_pass(self):
        """All valid types should pass validation."""
        valid_types = ["string", "boolean", "number", "time", "string_array", "number_array"]
        for valid_type in valid_types:
            widget = {
                "data_sources": [{
                    "measures": [{
                        "meerkat_schema": {"type": valid_type}
                    }]
                }]
            }
            errors = self.rule.validate(widget)
            assert len(errors) == 0, f"Type '{valid_type}' should be valid"

    def test_invalid_type_text(self):
        """Type 'text' should fail (use 'string' instead)."""
        widget = {
            "data_sources": [{
                "measures": [{
                    "meerkat_schema": {"type": "text"}
                }]
            }]
        }
        errors = self.rule.validate(widget)
        assert len(errors) == 1
        assert errors[0].rule_id == "INVALID_MEERKAT_PROJECTION_TYPE"
        assert "string" in errors[0].suggestion  # Should suggest valid types

    def test_invalid_type_array(self):
        """Type 'array' should fail (use 'string_array' or 'number_array')."""
        widget = {
            "data_sources": [{
                "measures": [{
                    "meerkat_schema": {"type": "array"}
                }]
            }]
        }
        errors = self.rule.validate(widget)
        assert len(errors) == 1
        assert "string_array" in errors[0].suggestion or "number_array" in errors[0].suggestion

    def test_dimension_validation(self):
        """Dimensions should also be validated."""
        widget = {
            "data_sources": [{
                "dimensions": [{
                    "meerkat_schema": {"type": "object"}  # Invalid
                }]
            }]
        }
        errors = self.rule.validate(widget)
        assert len(errors) == 1
        assert "dimensions" in errors[0].field_path


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
