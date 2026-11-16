"""Visualization validation rules."""

import sys
from pathlib import Path
from typing import Dict, Any, List
from ..core.rule import ValidationRule
from ..core.models import ValidationError

# Add scripts directory to path for config import
SCRIPTS_DIR = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

from config import CARTESIAN_CHART_TYPES


class ChartArrayStructureRule(ValidationRule):
    """Line/bar/column charts must use objects (not strings) in x/y arrays.

    This catches the split() error: DevRev UI calls .reference_name.split('.')
    on x/y array elements, which fails if elements are strings instead of objects.
    """

    @property
    def rule_id(self) -> str:
        return "CHART_ARRAY_STRUCTURE"

    @property
    def description(self) -> str:
        return "Chart x/y arrays must contain objects with reference_name, not strings"

    def validate(self, widget: Dict[str, Any]) -> List[ValidationError]:
        errors = []

        for sw_idx, sub_widget in enumerate(widget.get('sub_widgets', [])):
            viz = sub_widget.get('visualization', {})
            viz_type = viz.get('type')

            if viz_type not in CARTESIAN_CHART_TYPES:
                continue

            chart_config = viz.get(viz_type, {})

            # Check x array - elements must be objects, not strings
            x_array = chart_config.get('x', [])
            for i, x_item in enumerate(x_array):
                if isinstance(x_item, str):
                    errors.append(ValidationError(
                        rule_id=self.rule_id,
                        severity="error",
                        field_path=f"sub_widgets[{sw_idx}].visualization.{viz_type}.x[{i}]",
                        message=f"x[{i}] is string, must be object",
                        suggestion=(
                            f'{{"reference_name": "{x_item}", "label": "..."}}. '
                            "See the **widget-development** skill reference `references/visualization-patterns.md` → 'Chart x/y Arrays Must Be Objects'"
                        )
                    ))
                elif isinstance(x_item, dict) and 'reference_name' not in x_item:
                    errors.append(ValidationError(
                        rule_id=self.rule_id,
                        severity="error",
                        field_path=f"sub_widgets[{sw_idx}].visualization.{viz_type}.x[{i}]",
                        message=f"x[{i}] missing reference_name",
                        suggestion="Add reference_name pointing to dimension. See **widget-development** skill `references/visualization-patterns.md`"
                    ))

            # Check y array - elements must be objects, not strings
            y_array = chart_config.get('y', [])
            for i, y_item in enumerate(y_array):
                if isinstance(y_item, str):
                    errors.append(ValidationError(
                        rule_id=self.rule_id,
                        severity="error",
                        field_path=f"sub_widgets[{sw_idx}].visualization.{viz_type}.y[{i}]",
                        message=f"y[{i}] is string, must be object",
                        suggestion=(
                            f'{{"reference_name": "{y_item}", "label": "...", "color": {{"type": "static", "static": "chart-category-1-base"}}}}. '
                            "See **widget-development** skill `references/visualization-patterns.md`"
                        )
                    ))
                elif isinstance(y_item, dict) and 'reference_name' not in y_item:
                    errors.append(ValidationError(
                        rule_id=self.rule_id,
                        severity="error",
                        field_path=f"sub_widgets[{sw_idx}].visualization.{viz_type}.y[{i}]",
                        message=f"y[{i}] missing reference_name",
                        suggestion="Add reference_name pointing to measure. See **widget-development** skill `references/visualization-patterns.md`"
                    ))

        return errors


class MetricVisualizationRule(ValidationRule):
    """Metric visualization must have y as array of objects.

    This catches the forEach error: DevRev UI calls metric.y.forEach()
    which fails if y is not an array or contains non-object elements.
    """

    @property
    def rule_id(self) -> str:
        return "METRIC_VISUALIZATION_STRUCTURE"

    @property
    def description(self) -> str:
        return "Metric visualization y field must be an array of objects with reference_name and label"

    def validate(self, widget: Dict[str, Any]) -> List[ValidationError]:
        errors = []

        for sw_idx, sub_widget in enumerate(widget.get('sub_widgets', [])):
            viz = sub_widget.get('visualization', {})
            viz_type = viz.get('type')

            if viz_type != 'metric':
                continue

            metric_config = viz.get('metric', {})

            # Check y field exists
            if 'y' not in metric_config:
                errors.append(ValidationError(
                    rule_id='REQUIRED_FIELD',
                    severity='error',
                    field_path=f'sub_widgets[{sw_idx}].visualization.metric.y',
                    message='Required field "y" is missing from metric visualization',
                    suggestion=(
                        'Add "y": [{"reference_name": "...", "label": "..."}]. '
                        'See **widget-development** skill `references/visualization-patterns.md` → "Metric Visualization"'
                    )
                ))
                continue  # Can't validate structure if missing

            y_field = metric_config['y']

            # Check y is an array (not object or other type)
            if not isinstance(y_field, list):
                errors.append(ValidationError(
                    rule_id='INVALID_TYPE',
                    severity='error',
                    field_path=f'sub_widgets[{sw_idx}].visualization.metric.y',
                    message=f'metric.y must be an array, got {type(y_field).__name__}. '
                           f'Correct: "y": [{{"reference_name": "...", "label": "..."}}]',
                    suggestion=(
                        'Wrap the object in an array: "y": [{...}]. '
                        'See **widget-development** skill `references/visualization-patterns.md` → "Metric Visualization"'
                    )
                ))
                continue  # Can't validate array elements if not array

            # Check array is not empty
            if len(y_field) == 0:
                errors.append(ValidationError(
                    rule_id='INVALID_ARRAY',
                    severity='error',
                    field_path=f'sub_widgets[{sw_idx}].visualization.metric.y',
                    message='metric.y array must contain at least one element',
                    suggestion='Add at least one metric: "y": [{"reference_name": "...", "label": "..."}]'
                ))
                continue

            # Validate each array element
            for i, item in enumerate(y_field):
                if not isinstance(item, dict):
                    errors.append(ValidationError(
                        rule_id='INVALID_TYPE',
                        severity='error',
                        field_path=f'sub_widgets[{sw_idx}].visualization.metric.y[{i}]',
                        message=f'metric.y[{i}] must be an object, got {type(item).__name__}',
                        suggestion='Use object with reference_name and label'
                    ))
                    continue

                # Check reference_name
                if 'reference_name' not in item:
                    errors.append(ValidationError(
                        rule_id='REQUIRED_FIELD',
                        severity='error',
                        field_path=f'sub_widgets[{sw_idx}].visualization.metric.y[{i}].reference_name',
                        message='Required field "reference_name" is missing',
                        suggestion='Add reference_name pointing to measure (e.g., "data.count")'
                    ))

                # Check label
                if 'label' not in item:
                    errors.append(ValidationError(
                        rule_id='REQUIRED_FIELD',
                        severity='error',
                        field_path=f'sub_widgets[{sw_idx}].visualization.metric.y[{i}].label',
                        message='Required field "label" is missing',
                        suggestion='Add label for display (e.g., "P90 Response Time")'
                    ))

        return errors
