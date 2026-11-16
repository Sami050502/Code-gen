# Dashboard Scripts

Scripts for validating and managing DevRev dashboards.

## validate_dashboard.py

Validates dashboard JSON structure and optionally calls DevRev API for full validation.

### Usage

```bash
python validate_dashboard.py <project_root> <dashboard_file> [--quiet] [--no-api]
```

### Arguments

- `project_root` - Path to project root directory
- `dashboard_file` - Path to dashboard JSON file (absolute or relative to project_root)
- `--quiet` - Suppress output (only exit code matters)
- `--no-api` - Skip API validation (structure only)

### Exit Codes

- `0` - Validation passed
- `1` - Fatal error (file not found, invalid JSON)
- `2` - Validation failed (structure or API errors)

### Examples

```bash
# Validate a dashboard (full validation)
python validate_dashboard.py . dashboards/sales-overview.json

# Structure validation only (skip API)
python validate_dashboard.py . dashboards/sales-overview.json --no-api

# Quiet mode (for scripts/hooks)
python validate_dashboard.py . dashboards/sales-overview.json --quiet
```

### Validation Stages

#### Stage 1: Structure Validation (Local)

Checks:
- Required fields (title, version, layout, widgets)
- Version is "v0"
- Widget count ≤ 300
- Tab widget count ≤ 50 (recursive)
- Reference IDs are unique
- Grid positions are valid (x < 12, x+width ≤ 12, y ≥ 0, width/height ≥ 1)
- Widget DONs match DON format
- Hierarchy is valid (tabs > sections > widgets)

#### Stage 2: API Validation (Remote)

Checks (via DevRev API):
- Widget DONs are accessible
- Dashboard schema is valid
- Organization-specific rules

### Error Codes

| Code | Description |
|------|-------------|
| `MISSING_REQUIRED_FIELD` | Missing required field (title, version, layout, widgets) |
| `INVALID_VERSION` | Version is not "v0" |
| `MAX_WIDGETS_EXCEEDED` | Total widget count > 300 |
| `TAB_WIDGET_LIMIT_EXCEEDED` | Tab widget count > 50 (recursive) |
| `DUPLICATE_REFERENCE_ID` | reference_id used multiple times |
| `MISSING_COMPONENT_DEFINITION` | Layout reference has no matching component |
| `MISSING_POSITION` | Layout item has no position defined |
| `MISSING_POSITION_FIELD` | Position missing required field (x, y, width, height) |
| `INVALID_GRID_X` | x is out of bounds (must be 0-11) |
| `INVALID_GRID_Y` | y is out of bounds (must be ≥ 0) |
| `INVALID_GRID_WIDTH` | width is out of bounds (must be 1-12) |
| `INVALID_GRID_HEIGHT` | height is out of bounds (must be ≥ 1) |
| `GRID_OVERFLOW` | x + width > 12 (overflows grid) |
| `MISSING_WIDGET_ID` | Widget has no widget_id |
| `INVALID_WIDGET_DON` | widget_id is not valid DON format |
| `INVALID_HIERARCHY` | Hierarchy rules violated (e.g., nested tabs) |
| `API_VALIDATION_ERROR` | DevRev API reported validation error |

### Example Output

#### Success

```
VALIDATION PASSED

Warnings:
  [WARNING] API_UNAVAILABLE: DevRev API client not available, skipping API validation
```

#### Failure

```
VALIDATION FAILED

Errors:
  [ERROR] GRID_OVERFLOW: Item 'widget_3' overflows grid: x=8, width=6 (x+width=14 > 12)
  [ERROR] DUPLICATE_REFERENCE_ID: reference_id 'widget_1' is used multiple times
  [ERROR] TAB_WIDGET_LIMIT_EXCEEDED: Tab 'tab_overview' has 60 widgets (max 50)
```

### Integration with Hooks

This script is called by the PostToolUse validation hook:

```bash
# hooks/scripts/validate-dashboard-generation.sh
python scripts/dashboard/validate_dashboard.py . "$DASHBOARD_FILE" --quiet

exit_code=$?
if [ $exit_code -eq 2 ]; then
  # Feed errors to Claude for iteration
  python scripts/dashboard/validate_dashboard.py . "$DASHBOARD_FILE"
fi
exit $exit_code
```

### Dependencies

- Python 3.8+
- DevRevWidgetClient (optional, for API validation)

### Testing

```bash
# Test with valid dashboard
python validate_dashboard.py . skills/dashboard-development/examples/simple-dashboard.json

# Test with invalid dashboard (should fail)
echo '{"title":"Test","version":"v0","layout":[],"widgets":[]}' > test-dashboard.json
python validate_dashboard.py . test-dashboard.json

# Test structure only
python validate_dashboard.py . dashboards/my-dashboard.json --no-api
```

## Future Scripts

- `create_dashboard.py` - Create dashboard via API
- `clone_dashboard.py` - Clone existing dashboard
- `update_dashboard.py` - Update dashboard metadata
