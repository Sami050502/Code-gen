"""Semantic validator with rule engine."""

from pathlib import Path
from typing import Dict, Any, List, Optional
from ..core.models import ValidationResult, Stage
from ..core.rule import ValidationRule
from ..rules import sql_rules, viz_rules, structural_rules, type_mapping_rules, field_schema_rules, enum_validation_rules


class SemanticValidator:
    """Rule engine that orchestrates all semantic validation rules."""
    
    def __init__(self, rules: List[ValidationRule] = None, workspace_path: Optional[Path] = None, 
                 pat: Optional[str] = None, endpoint: Optional[str] = None):
        """
        Initialize semantic validator.
        
        Args:
            rules: List of validation rules. If None, uses default rules.
            workspace_path: Path to workspace for schema-aware validation.
            pat: DevRev Personal Access Token (for on-demand schema fetching).
            endpoint: DevRev API endpoint (for on-demand schema fetching).
        """
        self.workspace_path = Path(workspace_path) if workspace_path else None
        self.pat = pat
        self.endpoint = endpoint
        self.rules = rules or self._default_rules()
    
    def _default_rules(self) -> List[ValidationRule]:
        """Load validation rules that provide real value in API-only model.

        Philosophy: Only validate what we can reliably check locally.
        Let API handle everything else (business logic, complex semantics).

        Rules:
        - StructuralValidationRule: Schema-based validation (enums, required fields, constraints, visualization axes)
        - TypeMappingValidationRule: DevRev→Meerkat type mappings and aggregate function output types
        - SqlSchemaRule: Column validation against cached schemas (catches wrong field names)
        - ChartArrayStructureRule: x/y structure validation (prevents runtime split() errors)
        - FieldSchemaRules: Catches common field schema mistakes (display_name location, field_type vs type, etc.)

        These catch 75-85% of API validation errors locally.
        """
        from ..core.rule import FunctionBasedRule

        rules = [
            # 1. Structural Validation (schema-based, always applicable)
            structural_rules.StructuralValidationRule(),  # Enums, required fields, type consistency, constraints, visualization axes
            structural_rules.WidgetReferenceNameRule(),  # Reject reference_name at widget root
            structural_rules.WidgetNameRequiredRule(),  # Widget must have 'name' field
            structural_rules.ReferenceIdPatternRule(),  # reference_id must match ^[a-zA-Z][a-zA-Z0-9_]*$
            structural_rules.InvalidFieldDetectionRule(),  # Detect invalid fields (unit, sorts, angle, suffix)
            structural_rules.LayoutRequiredRule(),  # Widget must have 'layout' field
            structural_rules.TypeCompatibilityRule(),  # devrev_schema.field_type ↔ meerkat_schema.type compatibility
            structural_rules.WrappedFormatDetectionRule(),  # Detect DOWNLOAD format (outer 'widget' wrapper)
            structural_rules.InvalidFunctionLocationRule(),  # Detect function at wrong location (root, devrev_schema)
            structural_rules.SqlExpressionRequiredRule(),  # Measures must have non-empty sql_expression

            # 2. Enum Validation (prevent HTTP 406 errors from protobuf validator)
            enum_validation_rules.MeerkatFunctionTypeEnumRule(),  # function.type enum values (P50, P90, etc.)
            enum_validation_rules.WidgetVersionEnumRule(),  # version enum values (v0, v1, v2)
            enum_validation_rules.VisualizationTypeValidationRule(),  # visualization.type values (warning only)
            enum_validation_rules.MeerkatColumnProjectionTypeEnumRule(),  # meerkat_schema.type enum values

            # 3. Type Mapping Validation (runtime-enforced by backend)
            type_mapping_rules.TypeMappingValidationRule(),  # DevRev→Meerkat type mappings, aggregate function output types

            # 4. SQL Schema Validation (if schemas cached)
            sql_rules.SqlSchemaRule(
                workspace_path=self.workspace_path,
                pat=self.pat,
                endpoint=self.endpoint
            ),  # Syntax + column validation when schemas available

            # 5. Visualization Rules (structural validation)
            viz_rules.ChartArrayStructureRule(),  # x/y must be objects with reference_name
            viz_rules.MetricVisualizationRule(),  # metric.y must be array for forEach()
        ]

        # 6. Field Schema Rules (common field structure mistakes)
        for validator_func in field_schema_rules.FIELD_SCHEMA_VALIDATORS:
            rules.append(FunctionBasedRule(validator_func))

        return rules
    
    def validate(self, widget: Dict[str, Any]) -> ValidationResult:
        """
        Run all semantic validation rules.
        
        Args:
            widget: Widget JSON dictionary
            
        Returns:
            ValidationResult with all errors and warnings collected
        """
        result = ValidationResult(stage=Stage.SEMANTIC, valid=True)
        
        # Run each rule and collect errors/warnings
        for rule in self.rules:
            rule_errors = rule.validate(widget)
            
            for error in rule_errors:
                if error.severity == "error":
                    result.errors.append(error)
                    result.valid = False
                elif error.severity == "warning":
                    result.warnings.append(error)
        
        return result
