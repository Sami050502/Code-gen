"""Base validation rule class."""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Callable, Optional
from .models import ValidationError


class ValidationRule(ABC):
    """Base class for all validation rules."""

    @property
    @abstractmethod
    def rule_id(self) -> str:
        """Unique rule identifier."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable rule description."""
        pass

    @abstractmethod
    def validate(self, widget: Dict[str, Any]) -> List[ValidationError]:
        """
        Validate widget against this rule.

        Args:
            widget: Widget JSON dictionary

        Returns:
            List of ValidationError objects (empty if valid)
        """
        pass


class FunctionBasedRule(ValidationRule):
    """
    Adapter that wraps a simple validator function into a ValidationRule.

    Validator functions should have signature:
        (widget: Dict, spec: Dict) -> List[Dict]

    Where each Dict has: rule, severity, message, field (optional)
    These are converted to ValidationError objects with:
        - rule_id (from 'rule' key)
        - severity
        - field_path (from 'field' key, defaults to '')
        - message
        - suggestion (optional)
    """

    def __init__(self, validator_func: Callable, rule_id: str = None, description: str = None):
        """
        Initialize function-based rule.

        Args:
            validator_func: Function that validates widget
            rule_id: Optional rule ID (defaults to function name)
            description: Optional description (defaults to function docstring)
        """
        self._validator_func = validator_func
        self._rule_id = rule_id or validator_func.__name__
        self._description = description or (validator_func.__doc__ or "").strip()

    @property
    def rule_id(self) -> str:
        return self._rule_id

    @property
    def description(self) -> str:
        return self._description

    def validate(self, widget: Dict[str, Any]) -> List[ValidationError]:
        """Execute validator function and convert results to ValidationError objects."""
        try:
            # Call validator with widget and empty spec dict
            # Most validators don't currently use spec, but signature requires it
            results = self._validator_func(widget, {})

            # Convert dict results to ValidationError objects
            errors = []
            for r in results:
                errors.append(
                    ValidationError(
                        rule_id=r.get('rule', self._rule_id),
                        severity=r.get('severity', 'error'),
                        field_path=r.get('field', ''),
                        message=r.get('message', ''),
                        suggestion=r.get('suggestion')
                    )
                )
            return errors

        except Exception as e:
            # If validator function fails, return error as ValidationError
            return [
                ValidationError(
                    rule_id=f"{self._rule_id}_exception",
                    severity="error",
                    field_path="",
                    message=f"Validator function raised exception: {str(e)}",
                    suggestion="Check widget structure and validator implementation"
                )
            ]
