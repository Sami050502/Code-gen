"""Core validation data models."""

from dataclasses import dataclass, asdict, field
from typing import List, Optional
from enum import Enum


class Stage(Enum):
    """Validation stage enumeration."""
    STRUCTURE = "structure"
    SEMANTIC = "semantic"
    API = "api"


@dataclass
class ValidationError:
    """Structured validation error with context."""
    rule_id: str
    severity: str  # "error" or "warning"
    field_path: str
    message: str
    suggestion: Optional[str] = None
    
    def to_dict(self):
        """Convert to dictionary, excluding None values."""
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class ValidationResult:
    """Result from a validation stage."""
    stage: Stage
    valid: bool
    errors: List[ValidationError] = field(default_factory=list)
    warnings: List[ValidationError] = field(default_factory=list)
    
    @property
    def error_count(self) -> int:
        """Number of errors."""
        return len(self.errors)
    
    @property
    def warning_count(self) -> int:
        """Number of warnings."""
        return len(self.warnings)
    
    def to_dict(self):
        """Convert to dictionary for JSON output."""
        return {
            "valid": self.valid,
            "stage_failed": None if self.valid else self.stage.value,
            "errors": [e.to_dict() for e in self.errors],
            "warnings": [w.to_dict() for w in self.warnings]
        }
