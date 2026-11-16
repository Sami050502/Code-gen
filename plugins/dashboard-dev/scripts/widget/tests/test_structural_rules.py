"""Tests for structural validation rules."""

import pytest
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from lib.rules.structural_rules import (
    WidgetNameRequiredRule,
    ReferenceIdPatternRule,
    InvalidFieldDetectionRule,
    LayoutRequiredRule,
)


class TestWidgetNameRequiredRule:
    """Tests for WidgetNameRequiredRule."""

    def setup_method(self):
        self.rule = WidgetNameRequiredRule()

    def test_valid_widget_with_name(self):
        """Widget with name field should pass."""
        widget = {
            "name": "my-widget",
            "title": "My Widget",
            "version": "v0",
        }
        errors = self.rule.validate(widget)
        assert len(errors) == 0

    def test_missing_name_field(self):
        """Widget without name field should fail."""
        widget = {
            "title": "My Widget",
            "version": "v0",
        }
        errors = self.rule.validate(widget)
        assert len(errors) == 1
        assert errors[0].rule_id == "MISSING_NAME_FIELD"

    def test_empty_name_field(self):
        """Widget with empty name field should fail."""
        widget = {
            "name": "",
            "title": "My Widget",
            "version": "v0",
        }
        errors = self.rule.validate(widget)
        assert len(errors) == 1
        assert errors[0].rule_id == "MISSING_NAME_FIELD"


class TestReferenceIdPatternRule:
    """Tests for ReferenceIdPatternRule."""

    def setup_method(self):
        self.rule = ReferenceIdPatternRule()

    def test_valid_reference_ids(self):
        """Valid reference_id patterns should pass."""
        valid_ids = ["chart1", "my_chart", "ticketCount", "A", "abc123"]
        for ref_id in valid_ids:
            widget = {
                "sub_widgets": [{"reference_id": ref_id}],
                "layout": [{"reference_id": ref_id}],
            }
            errors = self.rule.validate(widget)
            assert len(errors) == 0, f"'{ref_id}' should be valid"

    def test_invalid_reference_id_starts_with_number(self):
        """reference_id starting with number should fail."""
        widget = {
            "sub_widgets": [{"reference_id": "1chart"}],
            "layout": [],
        }
        errors = self.rule.validate(widget)
        assert len(errors) == 1
        assert errors[0].rule_id == "INVALID_REFERENCE_ID_PATTERN"

    def test_invalid_reference_id_with_hyphen(self):
        """reference_id with hyphen should fail."""
        widget = {
            "sub_widgets": [{"reference_id": "my-chart"}],
            "layout": [],
        }
        errors = self.rule.validate(widget)
        assert len(errors) == 1
        assert errors[0].rule_id == "INVALID_REFERENCE_ID_PATTERN"

    def test_invalid_reference_id_with_dot(self):
        """reference_id with dot should fail."""
        widget = {
            "sub_widgets": [{"reference_id": "chart.1"}],
            "layout": [],
        }
        errors = self.rule.validate(widget)
        assert len(errors) == 1
        assert errors[0].rule_id == "INVALID_REFERENCE_ID_PATTERN"


class TestInvalidFieldDetectionRule:
    """Tests for InvalidFieldDetectionRule."""

    def setup_method(self):
        self.rule = InvalidFieldDetectionRule()

    def test_valid_widget_no_invalid_fields(self):
        """Widget without invalid fields should pass."""
        widget = {
            "name": "my-widget",
            "title": "My Widget",
            "version": "v0",
        }
        errors = self.rule.validate(widget)
        assert len(errors) == 0

    def test_invalid_unit_field_at_root(self):
        """Widget with 'unit' field at root should fail."""
        widget = {
            "name": "my-widget",
            "unit": "ms",
        }
        errors = self.rule.validate(widget)
        assert len(errors) == 1
        assert errors[0].rule_id == "INVALID_FIELD"
        assert "unit" in errors[0].message

    def test_invalid_sorts_field_at_root(self):
        """Widget with 'sorts' field at root should fail."""
        widget = {
            "name": "my-widget",
            "sorts": [{"field": "date", "direction": "desc"}],
        }
        errors = self.rule.validate(widget)
        assert len(errors) == 1
        assert errors[0].rule_id == "INVALID_FIELD"
        assert "sorts" in errors[0].message

    def test_invalid_type_field_at_root(self):
        """Widget with 'type' field at root should fail."""
        widget = {
            "name": "my-widget",
            "type": "chart",
        }
        errors = self.rule.validate(widget)
        assert len(errors) == 1
        assert errors[0].rule_id == "INVALID_FIELD"
        assert "type" in errors[0].message

    def test_invalid_unit_field_in_measure(self):
        """Measure with 'unit' field should fail."""
        widget = {
            "name": "my-widget",
            "data_sources": [{
                "reference_name": "data",
                "measures": [{
                    "reference_name": "count",
                    "unit": "tickets",
                }]
            }]
        }
        errors = self.rule.validate(widget)
        assert len(errors) == 1
        assert errors[0].rule_id == "INVALID_FIELD"


class TestLayoutRequiredRule:
    """Tests for LayoutRequiredRule."""

    def setup_method(self):
        self.rule = LayoutRequiredRule()

    def test_valid_widget_with_layout(self):
        """Widget with layout field should pass."""
        widget = {
            "name": "my-widget",
            "layout": [{"reference_id": "chart1", "position": {"x": 0, "y": 0}}],
        }
        errors = self.rule.validate(widget)
        assert len(errors) == 0

    def test_missing_layout_field(self):
        """Widget without layout field should fail."""
        widget = {
            "name": "my-widget",
            "title": "My Widget",
        }
        errors = self.rule.validate(widget)
        assert len(errors) == 1
        assert errors[0].rule_id == "MISSING_LAYOUT_FIELD"

    def test_empty_layout_array(self):
        """Widget with empty layout array should fail."""
        widget = {
            "name": "my-widget",
            "layout": [],
        }
        errors = self.rule.validate(widget)
        assert len(errors) == 1
        assert errors[0].rule_id == "MISSING_LAYOUT_FIELD"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
