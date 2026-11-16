# Widget Errors & Debugging

Error reference and debugging guide for DevRev widgets.

## Quick Error Reference

| Error | Cause | Fix |
|-------|-------|-----|
| `Missing required field: name` | Missing `devrev_schema.name` in measures/dimensions | Add `name`, `data_name`, `db_name` (all = `reference_name`) to devrev_schema |
| `v1 must use data_view` | Missing version | Add `"version": "v0"` |
| `InvalidArgument` (type mismatch) | Wrong devrev→meerkat type | See validation-schema.yaml for mappings |
| Widget blank, no error | Missing layout | Add layout array |
| `Cannot read...split` | Strings in x/y arrays | Use objects: `[{"reference_name": "..."}]` |
| `must appear in GROUP BY` | Window function issue | Pre-aggregate in OASIS (see sql-constraints.md) |
| `syntax error at or near "}"` | {MEERKAT} outside OVER() | Only use {MEERKAT} inside window functions |
| `non-inner join on subquery` | LEFT JOIN on CTE | Join base tables directly |
| Table not found | Missing prefix | Use `devrev.table_name` |
| Query timeout | Complex query | Add WHERE filters, reduce JOINs |
| Unsupported type | Using composite, []bool, etc | See validation-schema.yaml for supported types |
| `Unimplemented type for cast` | TIMESTAMP→BIGINT cast | Use `EXTRACT(EPOCH FROM ts)` |
| `-(DOUBLE, VARCHAR)` mismatch | Timestamp arithmetic | Extract epoch from both operands |
| `is_deleted = 'false'` fails | Boolean as string | Use `is_deleted = false` |
| `created_date != ''` fails | Timestamp as string | Use `created_date IS NOT NULL` |

---

## Silent Failures (No Error Message)

### Missing Layout Array

Widget renders blank with no error.

```json
// WRONG
{"data_sources": [...], "sub_widgets": [...]}

// CORRECT
{
  "data_sources": [...],
  "sub_widgets": [...],
  "layout": [{"position": {"height": 2, "width": 3, "x": 0, "y": 0}, "reference_id": "widget1"}]
}
```

### Missing Version Field

**Error**: `Bad request: v1 widgets must use data_view data sources only`

```json
// WRONG - defaults to v1
{"title": "...", "data_sources": [...]}

// CORRECT
{"version": "v0", "title": "...", "data_sources": [...]}
```

### Missing Name Field

**Error**: `Missing required field: name` (from API validation)

**IMPORTANT**: This error is misleading! It refers to `devrev_schema.name` in measures/dimensions, NOT the widget root-level `name` field.

**Three different "name" fields exist**:
1. **Widget root `name`** - OPTIONAL (unique per org if provided)
2. **`devrev_schema.name`** - REQUIRED in all measures/dimensions (must equal `reference_name`)
3. **Dashboard root `name`** - OPTIONAL (not unique)

**Required fields in devrev_schema**:
```json
{
  "reference_name": "total_count",
  "devrev_schema": {
    "field_type": "int",
    "name": "total_count",        // ✅ REQUIRED - equals reference_name
    "data_name": "total_count",   // ✅ REQUIRED - equals reference_name
    "db_name": "total_count",     // ✅ REQUIRED - equals reference_name
    "is_filterable": false,
    "ui": {"display_name": "Total Count"}
  },
  "meerkat_schema": {
    "type": "number",
    "sql_expression": "COUNT(*)"
  }
}
```

**Rule**: For EVERY measure and dimension, set:
- `devrev_schema.name = reference_name`
- `devrev_schema.data_name = reference_name`
- `devrev_schema.db_name = reference_name`

**Common mistakes**:
- Missing `devrev_schema.name` in measures or dimensions
- Assuming error refers to widget root-level `name` (it doesn't!)
- Setting only `name` without `data_name` and `db_name`

---

## Type Mapping Errors

### InvalidArgument: Type Mismatch

**Error**: `devrev schema type 'X' cannot be used with meerkat schema type 'Y'`

DevRev types must map to correct Meerkat types. See `validation-schema.yaml#type_mappings` for the complete mapping.

Common mappings:
- `int`, `double` → `number`
- `text`, `enum`, `id` → `string`
- `timestamp`, `date` → `time`
- `[]int`, `[]double` → `number_array`
- `[]text`, `[]id` → `string_array`

### Unsupported Type

**Error**: `devrev schema type 'X' is not supported`

Unsupported types: `composite`, `[]bool`, `[]date`, `[]timestamp`

### Aggregate Function Output Type

**Error**: Aggregate functions have specific output type requirements.

- `COUNT`, `SUM`, `AVG`, `MEDIAN` → must use `meerkat_schema.type: "number"`
- `MIN`, `MAX` → preserve input type

---

## Visualization Errors

### Chart Arrays Use Strings Instead of Objects

**Error**: `Cannot read properties of undefined (reading 'split')`

```json
// WRONG
"x": ["data.date"]

// CORRECT
"x": [{"reference_name": "data.date", "label": "Date"}]
```

### Color as String

```json
// WRONG
"color": "blue"

// CORRECT
"color": {"type": "static", "static": "chart-category-1-base"}
```

---

## Query Errors

### Timestamp Cast Error

**Error**: `Conversion Error: Unimplemented type for cast (TIMESTAMP WITH TIME ZONE -> BIGINT)`

```sql
-- WRONG
CAST(created_date AS BIGINT)

-- CORRECT
CAST(EXTRACT(EPOCH FROM created_date) AS BIGINT)
```

### Timestamp Arithmetic Type Mismatch

**Error**: `No function matches the given name and argument types '-(DOUBLE, VARCHAR)'`

```sql
-- WRONG
EXTRACT(EPOCH FROM CURRENT_TIMESTAMP) - last_message_timestamp

-- CORRECT
EXTRACT(EPOCH FROM CURRENT_TIMESTAMP) - EXTRACT(EPOCH FROM last_message_timestamp)
-- OR use DATEDIFF
DATEDIFF('day', last_message_timestamp, CURRENT_TIMESTAMP)
```

### Boolean String Comparison

**Error**: Type mismatch or unexpected results

```sql
-- WRONG
WHERE is_deleted = 'false'

-- CORRECT
WHERE is_deleted = false
WHERE NOT is_deleted
```

### Timestamp Empty String Check

**Error**: Type mismatch comparing timestamp to string

```sql
-- WRONG
WHERE created_date != ''

-- CORRECT
WHERE created_date IS NOT NULL
```

### Rolling Distinct Count

**Error**: `column "X" must appear in the GROUP BY clause`

This happens when using `COUNT(DISTINCT column)` inside a window function, but the column isn't a dimension.

**Fix**: Pre-aggregate in OASIS query. See `sql-constraints.md` for the detailed pattern.

### {MEERKAT} Outside OVER()

**Error**: `Parser Error: syntax error at or near "}"`

```json
// WRONG
"sql_expression": "DATE_TRUNC('day', {MEERKAT}.created_date)"

// CORRECT - no {MEERKAT} in regular expressions
"sql_expression": "DATE_TRUNC('day', created_date)"
```

The `{MEERKAT}` placeholder is ONLY valid inside `OVER()` clauses.

### LEFT JOIN on CTE

**Error**: `Cannot perform non-inner join on subquery!`

```sql
-- WRONG
WITH base AS (SELECT * FROM devrev.dim_issue)
SELECT * FROM base LEFT JOIN devrev.dim_account a ON ...

-- CORRECT
SELECT * FROM devrev.dim_issue i
LEFT JOIN devrev.dim_account a ON i.account_id = a.id
```

### ANY() in JOIN

**Error**: `Cannot perform non-inner join on subquery!`

```sql
-- WRONG
LEFT JOIN devrev.dim_account a ON a.id = ANY(i.account_ids)

-- CORRECT
LEFT JOIN devrev.dim_account a ON i.account_ids[1] = a.id
```

### Missing devrev. Prefix

**Error**: Table not found

```sql
-- WRONG
SELECT * FROM dim_ticket

-- CORRECT
SELECT * FROM devrev.dim_ticket
```

---

## Runtime Constraints

| Constraint | Limit | Symptom |
|------------|-------|---------|
| Row limit | 1,000 | Truncated results |
| Timeout | 1.5s | Query timeout error |
| Concurrent queries | 8 | 503 errors |

**Timeout fixes**:
- Select only needed columns
- Add WHERE filters
- Reduce JOINs (max 2-3)
- Move aggregations to Meerkat layer

---

## Validation Commands

```bash
# Validate widget JSON
dashboard-sync widget validate widgets/name.json

# Query dataset fields
dashboard-sync dataset query dim_ticket

# Query live data via API
dashboard-sync dataset query --limit 5 dim_ticket
```

---

## Common Field Name Mistakes

Use `dashboard-sync dataset query` to verify exact field names.

| Wrong | Correct |
|-------|---------|
| `closed_date` | `actual_close_date` |
| `ticket_id` | `id` |
| `owner` | `owned_by_id` |
