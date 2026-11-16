# Widget Validator

Three-stage validation framework for DevRev widget JSON files.

## Validation Philosophy

**API validation is the FINAL AUTHORITY.**

Local validation provides **fast feedback for common errors** before API calls:
- Structure validation (required fields, enums, type consistency)
- SQL syntax and column validation (DuckDB)
- Chart structure validation
- Type mapping validation (DevRev → Meerkat types)

| Stage | Role | On Failure |
|-------|------|------------|
| Structure | JSON structure, enums, type mappings | ❌ Fail |
| Semantic | SQL syntax, column references, chart arrays | ❌ Fail (critical) / ⚠️ Warning |
| API | DevRev server (business logic) | ❌ Fail |

## Architecture

```
lib/
├── core/
│   ├── models.py          # ValidationError, ValidationResult, Stage
│   └── rule.py            # Base ValidationRule abstract class
├── schema/
│   ├── parser.py          # MosaicSchemaParser
│   ├── generator.py       # ValidationGenerator
│   └── cache.py           # Schema caching
├── validators/
│   ├── schema.py          # Structure validator
│   ├── dynamic.py         # Dynamic schema validator
│   ├── semantic.py        # Rule engine orchestrator
│   └── api.py             # DevRev API validator
└── rules/
    ├── sql_rules.py       # SQL validation (SqlSchemaRule)
    ├── viz_rules.py       # Visualization validation
    ├── structural_rules.py # Structure, enums, constraints
    └── type_mapping_rules.py # DevRev→Meerkat type mapping
```

## Validation Rules

### Structural Rules (`structural_rules.py`)

**StructuralValidationRule** - Comprehensive structure validation:
- Required fields (title, sub_widgets, reference_id, etc.)
- Enum values (visualization types, data source types, versions)
- Type-field consistency (type=line requires line config)
- Field constraints (max lengths, array sizes)
- Visualization required fields (x/y axes per chart type)

### Type Mapping Rules (`type_mapping_rules.py`)

**TypeMappingValidationRule** - Backend-enforced type mappings:
- DevRev → Meerkat type mapping (e.g., `int`→`number`, `text`→`string`)
- Aggregate function output types (COUNT/SUM/AVG must use `number`)
- Unsupported type detection (`composite`, `[]bool`, `[]date`, `[]timestamp`)

Source: `mosaic/internal/utils/constants.go` (RequiredDevrevToMeerkatTypeMap)

### SQL Rules (`sql_rules.py`)

**SqlSchemaRule** (`SQL_SCHEMA`) - **CRITICAL**
- SQL syntax validation via DuckDB EXPLAIN
- Column reference validation against cached schemas
- Catches: wrong column names, syntax errors, missing tables
- Suggests similar columns when not found
- Detects permission issues (DATASET_PERMISSION_DENIED)

### Visualization Rules (`viz_rules.py`)

**ChartArrayStructureRule** (`CHART_ARRAY_STRUCTURE`) - **CRITICAL**
- Chart x/y arrays must contain objects, not strings
- Prevents frontend split() errors
- Validates reference_name presence

## Usage

### Standard Validation (Recommended)

```bash
# Full validation - API is final authority
python validate_widget.py . --widget widgets/my-widget.json

# Structure must pass, semantic warnings shown, API decides final result
```

### Skip API Mode

```bash
# Skip API validation (local checks only)
python validate_widget.py . --widget widgets/my-widget.json --skip-api

# Useful for offline development or testing
```

### Configuration via .env

Create a `.env` file in your workspace:

```bash
# Required for API validation
DEVREV_PAT=your-personal-access-token

# Optional, defaults to https://api.devrev.ai
DEVREV_ENDPOINT=https://api.devrev.ai

# Optional, enables JSON output mode
DASHBOARD_DEV_QUIET=1
```

### Output Modes

#### Normal Mode (Default)
```
Validating widget: My Dashboard Widget
   File: /path/to/widget.json

Stage 1: Structure Validation
  ✅ Structure valid

Stage 2: Semantic Validation
  ✅ All rules passed

Stage 3: API Validation (Final Authority)
  ✅ API validation passed

✅ Widget is valid!
```

#### Quiet Mode (JSON)
Enable with `--quiet` flag or `DASHBOARD_DEV_QUIET=1`:

```json
{
  "valid": true,
  "stage_failed": null,
  "errors": [],
  "warnings": []
}
```

### Error Output Example

```json
{
  "valid": false,
  "stage_failed": "structure",
  "errors": [
    {
      "rule_id": "TYPE_MAPPING_MISMATCH",
      "severity": "error",
      "field_path": "data_sources[0].measures[0].meerkat_schema.type",
      "message": "devrev schema type 'int' cannot be used with meerkat schema type 'string'",
      "suggestion": "Use meerkat type 'number' for devrev type 'int'"
    }
  ],
  "warnings": []
}
```

## Exit Codes

- `0` - Widget is valid (API passed, or API skipped and structure passed)
- `1` - Validation failed (structure error or API error)
- `130` - Interrupted by user (Ctrl+C)

## Command Line Options

| Option | Description |
|--------|-------------|
| `--widget, -w` | Widget JSON file (required) |
| `--skip-api` | Skip API validation |
| `--quiet, -q` | JSON output mode |
| `--verbose, -v` | Verbose output |

## Extending the Validator

### Adding a New Validation Rule

1. Create a new rule class in the appropriate file (`lib/rules/`):

```python
from typing import Dict, Any, List
from ..core.rule import ValidationRule
from ..core.models import ValidationError

class MyCustomRule(ValidationRule):
    @property
    def rule_id(self) -> str:
        return "MY_CUSTOM_RULE"
    
    @property
    def description(self) -> str:
        return "Description of what this rule validates"
    
    def validate(self, widget: Dict[str, Any]) -> List[ValidationError]:
        errors = []
        # Your validation logic here
        # Add errors as needed
        return errors
```

2. Register the rule in `lib/validators/semantic.py`:

```python
def _default_rules(self) -> List[ValidationRule]:
    return [
        # ... existing rules ...
        my_module.MyCustomRule(),
    ]
```

## Integration with dashboard-dev Plugin

This validator is designed to integrate with the dashboard-dev plugin ecosystem:

- Uses shared `logger` module from `scripts/common/lib/logger.py`
- Uses `DevRevWidgetClient` from `scripts/common/lib/devrev_widget_client.py`
- Respects `DASHBOARD_DEV_QUIET` environment variable
- Compatible with workspace structure and .env configuration

## Dependencies

- Python 3.8+
- `pyyaml` - YAML schema file parsing
- `duckdb` - SQL syntax and column validation
- `requests` - HTTP client (for API validation)

Install via:
```bash
pip install -r ${CLAUDE_PLUGIN_ROOT}/scripts/widget/requirements.txt
```

## Testing

```bash
cd plugins/dashboard-dev/scripts/widget
python -m pytest tests/ -v
```

All 29 tests cover schema parsing, validation generation, and dynamic validation.

## Related Documentation

- `SCHEMA_VALIDATION.md` - Schema-driven validation architecture
- `lib/core/SQL_AST_GUIDE.md` - SQL AST parsing guide
- `mosaic-schema.yaml` - Widget structure schema
