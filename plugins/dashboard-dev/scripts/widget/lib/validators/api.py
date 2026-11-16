"""API validator using DevRev widget validation endpoint."""

import re
from typing import Dict, Any, Optional, Tuple
from pathlib import Path

from ..core.models import ValidationResult, ValidationError, Stage


# Common API error patterns and their enhanced messages
API_ERROR_PATTERNS = [
    # Version errors
    (r'v1.*data_view|data_view.*v1',
     "Widget version mismatch: v1 widgets must use data_view data sources",
     'Change "version": "v1" to "version": "v0" for OASIS data sources'),

    # Field name matching errors
    (r'data_name|reference_name.*match|name.*mismatch',
     "Field name configuration error - names must match",
     "Ensure reference_name = name = data_name = db_name = oasis.name for all fields"),

    # Filterability errors
    (r'is_filterable|filterable',
     "Field filterability configuration error",
     "Measures must have is_filterable: false, dimensions must have is_filterable: true"),

    # Layout errors
    (r'layout.*required|missing.*layout',
     "Layout configuration error - layout array required",
     "Add layout array with position {height, width, x, y} and reference_id for each sub_widget"),

    # Field type errors
    (r'field_type.*double|aggregat.*int',
     "Measure field type error - aggregated measures need field_type: double",
     "Change field_type from 'int' to 'double' for measures with COUNT/SUM/AVG"),

    # ID type errors
    (r'id_type.*required|missing.*id_type',
     "ID field missing id_type configuration",
     "Add id_type array (e.g., [\"dev_user\"], [\"account\"]) to ID fields"),

    # Chart structure errors
    (r'x_axis|y_axes|reference_name.*required',
     "Chart axis configuration error",
     "Use x and y arrays with objects containing reference_name and label"),
]


class APIValidator:
    """Validates widget via DevRev API."""

    def __init__(self, pat: str = None, endpoint: str = None, env_file: Path = None):
        """
        Initialize API validator.

        Args:
            pat: DevRev Personal Access Token
            endpoint: API endpoint URL
            env_file: Path to .env file (alternative to pat/endpoint)
        """
        # Import here to avoid circular dependency
        from devrev_widget_client import DevRevWidgetClient

        if env_file:
            self.client = DevRevWidgetClient(env_file=env_file)
        elif pat and endpoint:
            self.client = DevRevWidgetClient(pat=pat, endpoint=endpoint)
        else:
            raise ValueError("Must provide either (pat, endpoint) or env_file")

    def _enhance_error_message(self, raw_message: str, debug_message: str = "") -> Tuple[str, str]:
        """
        Enhance raw API error with actionable message and suggestion.

        Returns:
            Tuple of (enhanced_message, suggestion)
        """
        combined = f"{raw_message} {debug_message}".lower()

        # Check against known error patterns
        for pattern, enhanced_msg, suggestion in API_ERROR_PATTERNS:
            if re.search(pattern, combined, re.IGNORECASE):
                return enhanced_msg, suggestion

        # Default enhancement - at least clean up the message
        return raw_message, "Review widget structure against the **widget-development** skill reference `references/quick-reference.md`"

    def validate(self, widget: Dict[str, Any]) -> ValidationResult:
        """
        Validate widget via DevRev API.
        
        Args:
            widget: Widget JSON dictionary
            
        Returns:
            ValidationResult with API validation results
        """
        result = ValidationResult(stage=Stage.API, valid=True)
        
        try:
            api_result = self.client.validate_widget(widget)
            
            if api_result.get("is_valid"):
                # Validation passed
                return result
            
            # Validation failed - extract ALL error information
            result.valid = False

            error_type = api_result.get('type', 'API_VALIDATION')
            field_name = api_result.get('field_name', '')
            debug_message = api_result.get('debug_message', '')
            message = api_result.get('message', 'API validation failed')
            allowed_values = api_result.get('allowed_values', [])
            actual_value = api_result.get('value', '')

            # Enhance error message with actionable suggestions
            enhanced_msg, enhanced_suggestion = self._enhance_error_message(message, debug_message)

            # Build comprehensive error message
            if debug_message and debug_message != message and enhanced_msg == message:
                # Only append debug_message if we didn't enhance it
                error_msg = f"{message}: {debug_message}"
            else:
                error_msg = enhanced_msg

            # Build suggestion with context
            suggestion_parts = []
            if enhanced_suggestion:
                suggestion_parts.append(enhanced_suggestion)
            if actual_value:
                suggestion_parts.append(f"Current value: {actual_value!r}")
            if allowed_values:
                suggestion_parts.append(f"Allowed values: {allowed_values}")

            suggestion = " | ".join(suggestion_parts) if suggestion_parts else "Review widget structure against the **widget-development** skill reference `references/quick-reference.md`"

            error = ValidationError(
                rule_id=error_type.upper().replace(' ', '_'),
                severity="error",
                field_path=field_name,
                message=error_msg,
                suggestion=suggestion
            )
            result.errors.append(error)
            
        except Exception as e:
            # API call failed
            result.valid = False
            error = ValidationError(
                rule_id="API_ERROR",
                severity="error",
                field_path="",
                message=f"API validation failed: {str(e)}",
                suggestion="Check network connectivity and credentials"
            )
            result.errors.append(error)
        
        return result
