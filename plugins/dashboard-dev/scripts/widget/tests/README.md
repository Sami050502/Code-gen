# Widget Validation Tests

This directory contains comprehensive tests for the schema-driven validation system.

## Test Structure

```
tests/
  unit/                           # Unit tests for individual components
    test_schema_parser.py         # MosaicSchemaParser tests
    test_validation_generator.py  # ValidationGenerator tests
  integration/                    # Integration tests
    test_dynamic_validator.py     # DynamicValidator end-to-end tests
```

## Running Tests

### Run All Tests
```bash
cd plugins/dashboard-dev/scripts/widget
python -m pytest tests/ -v
```

### Run Specific Test Suite
```bash
# Unit tests only
python -m pytest tests/unit/ -v

# Integration tests only
python -m pytest tests/integration/ -v

# Specific test file
python -m pytest tests/unit/test_schema_parser.py -v
```

### Run with Coverage
```bash
python -m pytest tests/ --cov=lib/schema --cov=lib/validators/dynamic --cov-report=html
```

## Test Coverage

### Unit Tests (18 tests)

**test_schema_parser.py** (9 tests)
- Parse object schemas
- Parse composite types
- Resolve field types
- Get schema version
- Get all object/composite type names
- Handle missing schemas
- Reload schema functionality

**test_validation_generator.py** (9 tests)
- Required field validation
- String max length validation
- String pattern validation
- Enum validation
- Boolean type validation
- Array length validation
- Composite type validation
- Complete object validation
- Tokens type (accepts any)

### Integration Tests (11 tests)

**test_dynamic_validator.py** (11 tests)
- Validate valid widget
- Missing required fields
- Field length violations
- Enum violations
- Composite type validation
- Nested composite validation
- Array validation
- Pattern validation
- Get schema version
- Refresh schema
- Invalid object type

## Test Results

All 29 tests pass successfully:
- ✅ 9/9 schema parser tests
- ✅ 9/9 validation generator tests
- ✅ 11/11 dynamic validator tests

**Total: 29/29 tests passing (100%)**

## Key Testing Patterns

### Temporary Schema Files
Tests create temporary schema files for isolated testing:
```python
@pytest.fixture
def sample_schema_file():
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(schema_content, f)
        temp_path = Path(f.name)
    yield temp_path
    temp_path.unlink()
```

### Validation Error Checking
Tests verify specific error types:
```python
errors = validator(invalid_value)
assert any('PATTERN_MISMATCH' in e.rule_id for e in errors)
```

### Integration Testing
Integration tests use the actual mosaic-schema.yaml:
```python
validator = DynamicValidator(object_type="widget")
result = validator.validate(widget)
assert result.valid is True
```

## Adding New Tests

When adding new features:

1. **Unit tests** for new schema components or validation rules
2. **Integration tests** for end-to-end validation scenarios
3. Update this README with new test descriptions
4. Ensure all tests pass before committing
