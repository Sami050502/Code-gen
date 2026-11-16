# SQL Patterns and Constraints

Detailed SQL patterns, constraints, and pitfalls for DevRev widget queries.

## DuckDB Dialect

All OASIS queries execute using DuckDB syntax and functions. Write queries using DuckDB-specific features and functions.

## Platform Constraints

| Constraint | Value | Notes |
|------------|-------|-------|
| Row limit | 1,000 | Automatic, non-configurable (runtime) |
| Query timeout | 1.5s | Simplify queries if timing out (runtime) |
| Table format | `devrev.<table>` | Always use prefix (runtime) |
| LEFT JOIN on CTE | Not supported | Join base tables directly (runtime) |
| ANY() in JOIN | Not supported | Use array indexing: `array[1]` (runtime) |

*Note: Constraints marked (runtime) are enforced by the API, not local validation.*

## Array Type Syntax

**CRITICAL**: DuckDB uses `ARRAY<TYPE>` syntax, not `TYPE[]`.

❌ **WRONG** - Causes runtime parser error:
```sql
CAST(json_extract(search_results, '$') AS JSON[])  -- Array syntax invalid
```

✅ **CORRECT** - Use DuckDB array syntax:
```sql
CAST(json_extract(search_results, '$') AS ARRAY<JSON>)
```

**Error message you'll see if you use wrong syntax**:
```
Parser Error: syntax error at or near "]"
```

**Why This Happens:**
- DuckDB uses `ARRAY<TYPE>` syntax for array types, not `TYPE[]`
- The `[]` syntax is invalid in CAST expressions
- This creates a parser error at runtime, after validation passes

**Solution:**
Always use `ARRAY<TYPE>` when casting to array types:
- `ARRAY<JSON>` for arrays of JSON objects
- `ARRAY<VARCHAR>` for arrays of strings
- `ARRAY<DOUBLE>` for arrays of numbers
- `ARRAY<BIGINT>` for arrays of integers

## CAST Type Constraints

**CRITICAL**: OASIS SQL (DuckDB) only supports specific numeric types in CAST expressions.

❌ **NEVER use these types**:
- `INTEGER` - Use `BIGINT` instead
- `INT` - Use `BIGINT` instead
- `FLOAT` - Use `DOUBLE` instead
- `REAL` - Use `DOUBLE` instead

✅ **ALWAYS use these types**:
- `BIGINT` - For integer values
- `DOUBLE` - For floating-point values
- `VARCHAR` - For text values
- `BOOLEAN` - For true/false values
- `DATE` - For date values
- `TIMESTAMP` - For datetime values

**Error you'll see if violated**:
```
UNSUPPORTED_CAST_TYPE: CAST to unsupported type: INTEGER
Suggestion: Use BIGINT instead of INTEGER
```

**Complete replacement table**:

| ❌ Don't Use | ✅ Use Instead | Example |
|-------------|---------------|---------|
| `INTEGER` | `BIGINT` | `CAST(count AS BIGINT)` |
| `INT` | `BIGINT` | `CAST(id AS BIGINT)` |
| `FLOAT` | `DOUBLE` | `CAST(avg AS DOUBLE)` |
| `REAL` | `DOUBLE` | `CAST(price AS DOUBLE)` |

**Why**: OASIS runtime only recognizes a specific set of type names. Standard SQL types like `INTEGER` fail validation.

**Examples**:

❌ **WRONG** - Using INTEGER:
```sql
SELECT
  ticket_id,
  CAST(priority AS INTEGER) AS priority_level  -- ❌ ERROR
FROM devrev.dim_ticket
```

✅ **CORRECT** - Using BIGINT:
```sql
SELECT
  ticket_id,
  CAST(priority AS BIGINT) AS priority_level  -- ✓ Supported type
FROM devrev.dim_ticket
```

❌ **WRONG** - Using FLOAT:
```sql
SELECT
  revenue,
  CAST(revenue * 0.1 AS FLOAT) AS tax  -- ❌ ERROR
FROM devrev.fact_sales
```

✅ **CORRECT** - Using DOUBLE:
```sql
SELECT
  revenue,
  CAST(revenue * 0.1 AS DOUBLE) AS tax  -- ✓ Supported type
FROM devrev.fact_sales
```

**Rule**: When casting numeric types in OASIS SQL, always use `BIGINT` for integers and `DOUBLE` for decimals.

## Safe Type Conversion with TRY_CAST

**CRITICAL**: When converting VARCHAR fields that may contain invalid or empty values, use `TRY_CAST` instead of `CAST` to avoid runtime errors.

### TRY_CAST vs CAST Behavior

| Function | On Invalid Value | On Empty String | On NULL |
|----------|------------------|-----------------|---------|
| `CAST(x AS BIGINT)` | **Error** | **Error** | NULL |
| `TRY_CAST(x AS BIGINT)` | NULL | NULL | NULL |

**Why This Matters**: VARCHAR fields that look numeric (e.g., `"123"`, `""`, `"N/A"`) will crash with `CAST` but safely return NULL with `TRY_CAST`.

### Pattern 1: VARCHAR to Numeric with Default

When you need a default value for invalid/empty strings:

```sql
SELECT
  id,
  COALESCE(TRY_CAST(view_count AS BIGINT), 0) AS views
FROM devrev.dim_article
```

**Use when**: Field stores numeric values as VARCHAR but may contain empty strings or non-numeric values.

### Pattern 2: Filter Invalid Values

When you want to exclude rows with invalid data:

```sql
SELECT
  id,
  TRY_CAST(duration AS BIGINT) AS duration_ms
FROM devrev.fact_events
WHERE TRY_CAST(duration AS BIGINT) IS NOT NULL
```

**Use when**: You only want rows with valid numeric values and can discard invalid ones.

### Pattern 3: Date Fields Stored as VARCHAR

When date-like fields are stored as VARCHAR:

```sql
SELECT
  id,
  TRY_CAST(publish_date AS DATE) AS published
FROM devrev.dim_article
WHERE TRY_CAST(publish_date AS DATE) IS NOT NULL
```

**Use when**: Date field is VARCHAR type but contains date strings like `"2024-01-15"`.

### Pattern 4: Boolean-like VARCHAR Fields

When boolean values are stored as VARCHAR strings:

```sql
SELECT
  id,
  CASE WHEN LOWER(is_active) = 'true' THEN true ELSE false END AS active
FROM devrev.dim_feature
```

**Use when**: Field contains `"true"`, `"false"`, `"TRUE"`, `"FALSE"` as strings.

### When to Use Each Pattern

| Scenario | Pattern | Example |
|----------|---------|---------|
| Need numeric value, have fallback | Pattern 1 (COALESCE) | `COALESCE(TRY_CAST(count AS BIGINT), 0)` |
| Only want valid rows | Pattern 2 (WHERE filter) | `WHERE TRY_CAST(amount AS DOUBLE) IS NOT NULL` |
| VARCHAR date for filtering | Pattern 3 (Date cast) | `TRY_CAST(date_field AS DATE)` |
| String "true"/"false" values | Pattern 4 (CASE) | `LOWER(flag) = 'true'` |

### Error Signatures

If you see these errors, switch from `CAST` to `TRY_CAST`:

```
Conversion Error: Could not convert string '' to INT64
Conversion Error: Could not convert string 'N/A' to DOUBLE
```

**See also**: `references/data-sampling.md` → "Detecting VARCHAR Numeric Fields" for how to identify these fields during data sampling.

## Timestamp Arithmetic

**CRITICAL**: DevRev stores timestamps as `TIMESTAMP WITH TIME ZONE`. Direct casting or arithmetic with timestamps requires specific patterns.

### Cannot Cast Timestamp to BIGINT

❌ **WRONG** - Causes runtime error:
```sql
CAST(created_date AS BIGINT)  -- Unimplemented type for cast (TIMESTAMP WITH TIME ZONE -> BIGINT)
```

✅ **CORRECT** - Extract epoch first:
```sql
CAST(EXTRACT(EPOCH FROM created_date) AS BIGINT)
```

**Error you'll see**:
```
Conversion Error: Unimplemented type for cast (TIMESTAMP WITH TIME ZONE -> BIGINT)
```

### Calculating Days Since a Timestamp

To calculate days between a timestamp and now:

❌ **WRONG** - Type mismatch (DOUBLE - VARCHAR):
```sql
EXTRACT(EPOCH FROM CURRENT_TIMESTAMP) - last_message_timestamp
-- Error: No function matches '-(DOUBLE, VARCHAR)'
```

❌ **WRONG** - Direct subtraction fails:
```sql
CURRENT_TIMESTAMP - created_date  -- Returns INTERVAL, not days
```

✅ **CORRECT** - Extract epoch from both sides:
```sql
CAST(
  (EXTRACT(EPOCH FROM CURRENT_TIMESTAMP) - EXTRACT(EPOCH FROM created_date)) / 86400
  AS BIGINT
) AS days_since_created
```

✅ **CORRECT** - Use DATEDIFF function:
```sql
DATEDIFF('day', created_date, CURRENT_TIMESTAMP) AS days_since_created
```

✅ **CORRECT** - Cast to DATE for simple day difference:
```sql
CURRENT_DATE - CAST(created_date AS DATE) AS days_since_created
```

### Filtering by Time Ranges

✅ **CORRECT** - Use INTERVAL for relative dates:
```sql
WHERE created_date >= CURRENT_TIMESTAMP - INTERVAL '30 days'
WHERE created_date >= CURRENT_DATE - INTERVAL '7 days'
```

✅ **CORRECT** - Use DATE_TRUNC for period boundaries:
```sql
WHERE created_date >= DATE_TRUNC('month', CURRENT_DATE)
WHERE created_date >= DATE_TRUNC('week', CURRENT_TIMESTAMP)
```

### Date Truncation for Grouping

✅ **CORRECT** - Truncate to day/week/month:
```sql
DATE_TRUNC('day', created_date) AS date
DATE_TRUNC('week', created_date) AS week_start
DATE_TRUNC('month', created_date) AS month_start
```

### Complete Example: Days Since Last Activity

```sql
SELECT
  id,
  display_id,
  DATEDIFF('day', last_message_timestamp, CURRENT_TIMESTAMP) AS days_inactive
FROM devrev.dim_conversation
WHERE last_message_timestamp IS NOT NULL
  AND DATEDIFF('day', last_message_timestamp, CURRENT_TIMESTAMP) > 30
```

### Complete Example: Age Buckets

```sql
SELECT
  id,
  CASE
    WHEN DATEDIFF('day', created_date, CURRENT_TIMESTAMP) < 7 THEN '< 1 week'
    WHEN DATEDIFF('day', created_date, CURRENT_TIMESTAMP) < 30 THEN '1-4 weeks'
    WHEN DATEDIFF('day', created_date, CURRENT_TIMESTAMP) < 90 THEN '1-3 months'
    ELSE '> 3 months'
  END AS age_bucket
FROM devrev.dim_ticket
```

## Boolean and String Comparisons

**CRITICAL**: DevRev fields use actual types, not string representations.

### Boolean Fields

❌ **WRONG** - Comparing to string:
```sql
WHERE is_deleted = 'false'   -- Boolean compared to string
WHERE is_deleted = 'true'    -- Boolean compared to string
```

✅ **CORRECT** - Use actual boolean:
```sql
WHERE is_deleted = false
WHERE is_deleted = true
WHERE NOT is_deleted         -- Equivalent to is_deleted = false
```

### Timestamp NULL Checks

❌ **WRONG** - Comparing timestamp to empty string:
```sql
WHERE created_date != ''     -- Timestamp is not a string
```

✅ **CORRECT** - Use IS NOT NULL:
```sql
WHERE created_date IS NOT NULL
```

### Type Summary for Common Fields

| Field Pattern | Actual Type | Correct Comparison |
|---------------|-------------|-------------------|
| `is_deleted`, `is_active` | BOOLEAN | `= true`, `= false` |
| `created_date`, `modified_date` | TIMESTAMP WITH TIME ZONE | `IS NOT NULL`, `>= date` |
| `status`, `priority` | VARCHAR | `= 'value'` |
| `count`, `version` | BIGINT | `= 0`, `> 10` |

## Rolling Distinct Count Trap

Using `COUNT(DISTINCT column)` in a window function **FAILS** at runtime with:
```
column "X" must appear in the GROUP BY clause
```

**Why**: Meerkat generates `GROUP BY` on dimensions. After grouping, the column no longer exists for the window function.

**Solution**: Pre-aggregate in OASIS by adding the column to GROUP BY. See two-layer architecture patterns in main skill.

## JSON Extraction

When extracting JSON fields, always handle missing keys:

❌ **WRONG** - Fails on missing key:
```sql
json_extract(metadata, '$.severity')
```

✅ **CORRECT** - Handles missing key:
```sql
COALESCE(json_extract(metadata, '$.severity'), 'unknown')
```

## NULL Handling

Always check for NULL before array operations:

❌ **WRONG** - Fails on NULL array:
```sql
array[1]
```

✅ **CORRECT** - Checks array length:
```sql
CASE WHEN array_length(tags) > 0 THEN tags[1] ELSE NULL END
```

## Query Performance

**Fact tables (>1M rows) REQUIRE filters** to avoid timeout:

❌ **WRONG** - Unfiltered fact table:
```sql
SELECT * FROM devrev.fact_transitions
```

✅ **CORRECT** - Filtered fact table:
```sql
SELECT * FROM devrev.fact_transitions
WHERE created_date >= CURRENT_DATE - INTERVAL '30 days'
```

## Table Prefixes

Always use `devrev.` prefix for table names:

❌ **WRONG**:
```sql
SELECT * FROM dim_ticket
```

✅ **CORRECT**:
```sql
SELECT * FROM devrev.dim_ticket
```

## Join Limitations

**LEFT JOIN on CTE not supported**. Join base tables directly:

❌ **WRONG**:
```sql
WITH recent_tickets AS (
  SELECT id, created_date FROM devrev.dim_ticket
  WHERE created_date >= CURRENT_DATE - INTERVAL '7 days'
)
SELECT t.id, c.subject
FROM recent_tickets t
LEFT JOIN devrev.dim_conversation c ON t.id = c.ticket_id  -- ❌ ERROR
```

✅ **CORRECT** - Join base tables first:
```sql
WITH enriched_tickets AS (
  SELECT
    t.id,
    t.created_date,
    c.subject
  FROM devrev.dim_ticket t
  LEFT JOIN devrev.dim_conversation c ON t.id = c.ticket_id
  WHERE t.created_date >= CURRENT_DATE - INTERVAL '7 days'
)
SELECT * FROM enriched_tickets
```
