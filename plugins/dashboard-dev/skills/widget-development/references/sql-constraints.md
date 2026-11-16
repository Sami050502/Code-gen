# SQL Constraints & Patterns

DevRev-specific SQL constraints and patterns. Standard DuckDB syntax applies unless noted here.

## Hard Limits

| Constraint | Value | Notes |
|------------|-------|-------|
| Row limit | 1,000 | Automatic, non-configurable |
| Timeout | 1.5 seconds | Query execution limit |
| Concurrent queries | 8 | Per session |

**Performance fixes**:
- Add WHERE filters
- Select specific columns (not `*`)
- Reduce JOINs (max 2-3 recommended)
- Move aggregations to Meerkat layer

---

## Two-Layer Architecture

DevRev uses a **two-layer query model**. Violating this causes runtime errors.

| Layer | Location | Purpose | Allowed |
|-------|----------|---------|---------|
| **OASIS** | `oasis.sql_query` | Raw data extraction | SELECT, FROM, JOIN, WHERE, CTE, CASE, JSON extraction, DATE_TRUNC |
| **Meerkat** | `meerkat_schema.sql_expression` | Aggregations | COUNT, SUM, AVG, MIN, MAX, PERCENTILE_CONT, window functions |

**Hard Rule**: Window functions (`OVER`) MUST be in Meerkat, never in OASIS.

### Query Generation Flow

1. OASIS returns raw rows
2. Meerkat generates `GROUP BY` from all declared dimensions
3. Meerkat wraps OASIS result and adds measure expressions
4. **Key insight**: After GROUP BY, only dimension columns exist

---

## The Rolling Distinct Count Trap

This is the most common window function error.

### Pattern That Fails

```json
{
  "oasis": {"sql_query": "SELECT activity_date, user_id FROM devrev.fact_engagement"},
  "dimensions": [{"reference_name": "activity_date"}],
  "measures": [{
    "sql_expression": "COUNT(DISTINCT user_id) OVER (ORDER BY {MEERKAT}.activity_date ROWS BETWEEN 29 PRECEDING AND CURRENT ROW)"
  }]
}
```

**Error**: `column "user_id" must appear in the GROUP BY clause`

### Why It Fails

Generated query:
```sql
SELECT
  activity_date,
  COUNT(DISTINCT user_id) OVER (ORDER BY activity_date ROWS BETWEEN 29 PRECEDING AND CURRENT ROW)
FROM oasis_result
GROUP BY activity_date  -- user_id is NOT here!
```

After `GROUP BY activity_date`, the `user_id` column no longer exists.

### Correct Pattern: Pre-Aggregate in OASIS

```json
{
  "oasis": {
    "sql_query": "SELECT activity_date, user_id FROM devrev.fact_engagement GROUP BY activity_date, user_id"
  },
  "dimensions": [{"reference_name": "activity_date"}],
  "measures": [{
    "sql_expression": "SUM(COUNT(*)) OVER (ORDER BY {MEERKAT}.activity_date ROWS BETWEEN 29 PRECEDING AND CURRENT ROW)"
  }]
}
```

**Why it works**: OASIS returns one row per unique (date, user) pair. Meerkat counts those rows per date, then windows the counts.

### Alternative: Aggregated Column IS the Dimension

When the aggregated column IS the dimension:

```json
{
  "oasis": {"sql_query": "SELECT id, created_date FROM devrev.dim_ticket"},
  "dimensions": [{"reference_name": "created_date", "meerkat_schema": {"sql_expression": "DATE_TRUNC('day', created_date)"}}],
  "measures": [{
    "sql_expression": "AVG(COUNT(DISTINCT id)) OVER (ORDER BY {MEERKAT}.created_date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW)"
  }]
}
```

**Why it works**: `id` is inside `COUNT(DISTINCT id)` which is an aggregate function. The aggregate "consumes" the column before the window function operates.

---

## {MEERKAT} Placeholder Rules

The `{MEERKAT}` prefix references the grouped dimension column.

### Only Valid Inside OVER() Clauses

```sql
-- CORRECT: Inside ORDER BY of OVER()
AVG(COUNT(*)) OVER (ORDER BY {MEERKAT}.created_date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW)

-- CORRECT: Inside PARTITION BY of OVER()
SUM(amount) OVER (PARTITION BY {MEERKAT}.account_id ORDER BY {MEERKAT}.date)
```

### Not Valid Elsewhere

```sql
-- WRONG: In regular dimension - causes parser error
"sql_expression": "DATE_TRUNC('day', {MEERKAT}.created_date)"

-- WRONG: In measure without window function
"sql_expression": "COUNT({MEERKAT}.id)"
```

**Error**: `Parser Error: syntax error at or near "}"`

---

## JOIN Constraints

### No LEFT JOIN on CTEs or Subqueries

```sql
-- WRONG: Platform rejects this
WITH base AS (SELECT * FROM devrev.dim_issue)
SELECT * FROM base b
LEFT JOIN devrev.dim_account a ON b.account_id = a.id

-- CORRECT: Join base tables directly
SELECT i.*, a.tier
FROM devrev.dim_issue i
LEFT JOIN devrev.dim_account a ON i.account_id = a.id
```

### No ANY() in JOIN Conditions

```sql
-- WRONG: ANY() treated as subquery
LEFT JOIN devrev.dim_account a ON a.id = ANY(i.account_ids)

-- CORRECT: Use array indexing
LEFT JOIN devrev.dim_account a ON i.account_ids[1] = a.id
```

---

## Table Naming

Always use `devrev.` prefix:

```sql
-- Correct
SELECT * FROM devrev.dim_ticket

-- Wrong (table not found)
SELECT * FROM dim_ticket
```

---

## JSONPath Limitations

DuckDB supports basic JSONPath only.

### Supported

```sql
json_extract(field, '$')           -- Root
json_extract(field, '$.key')       -- Single key
json_extract(field, '$[0]')        -- Array index
json_extract(field, '$[*]')        -- All array elements
```

### Not Supported

```sql
-- Filter expressions NOT supported
json_extract(field, '$[?(@.type=="x")]')
```

**Workaround**:
```sql
CASE WHEN 'x' = ANY(json_extract_string(field, '$[*].type'))
     THEN true ELSE false END
```

---

## JSON Field Extraction Patterns

DevRev stores complex data in JSON fields:

```sql
-- Extract string value
json_extract_string(annual_contract_value, '$.amount')

-- Extract and cast to number
CAST(json_extract_string(field, '$.value') AS DOUBLE)

-- Extract from array
json_extract_string(surveys_aggregation_json, '$[0].average')

-- UEnum field (stores ordinal values as JSON)
json_extract_string(severity_uenum_json, '$.label')
```

---

## Array Type Casting

### Supported CAST Types

**CRITICAL**: Meerkat query engine only supports specific CAST target types. Using unsupported types will cause parser errors at runtime.

#### Basic Types (Supported)
```sql
CAST(field AS VARCHAR)     ✓
CAST(field AS DOUBLE)      ✓
CAST(field AS BIGINT)      ✓
CAST(field AS BOOLEAN)     ✓
CAST(field AS TIMESTAMP)   ✓
```

#### Array Types (Supported)
```sql
CAST(array_column AS ARRAY<VARCHAR>)   ✓
CAST(array_column AS ARRAY<DOUBLE>)    ✓
CAST(array_column AS ARRAY<BIGINT>)    ✓
CAST(array_column AS ARRAY<BOOLEAN>)   ✓
```

#### Unsupported Types (Will Fail at Runtime)
```sql
CAST(field AS ARRAY<JSON>)       ✗ NOT SUPPORTED
CAST(field AS ARRAY<TIMESTAMP>)  ✗ NOT SUPPORTED
CAST(field AS JSON)               ✗ NOT SUPPORTED
```

**Error you'll see with unsupported types**:
```
Parser Error: syntax error at or near "ARRAY"
```

### DuckDB Array Type Syntax

DuckDB uses `ARRAY<TYPE>` syntax for array types, NOT the `TYPE[]` syntax common in other SQL dialects.

**CORRECT SYNTAX**:
```sql
CAST(array_column AS ARRAY<VARCHAR>)
CAST(list_column AS ARRAY<DOUBLE>)
```

**WRONG SYNTAX** (causes parser error):
```sql
CAST(json_extract(field, '$') AS JSON[])  -- ERROR: syntax error at or near "]"
CAST(...AS VARCHAR[])                      -- ERROR: Invalid type syntax
CAST(...AS INT[])                          -- ERROR: Invalid type syntax
```

### Working with JSON Arrays

Since `ARRAY<JSON>` is not supported, extract JSON to strings first:

**CORRECT - Extract to string array**:
```sql
-- Extract JSON array elements as strings
CAST(json_extract_string(field, '$') AS ARRAY<VARCHAR>)

-- For JSON objects, convert to string representation
json_extract_string(field, '$.nested_object')
```

**WRONG - Direct JSON array cast**:
```sql
-- This will FAIL at runtime
CAST(json_extract(field, '$') AS ARRAY<JSON>)
```

### UNNEST with Type Casting

When using UNNEST with type-casted arrays, use supported types only:

**CORRECT**:
```sql
-- Extract string array and iterate
WITH parsed AS (
  SELECT CAST(json_extract_string(data, '$.items') AS ARRAY<VARCHAR>) AS items
  FROM table_name
)
SELECT UNNEST(items) AS item
FROM parsed
```

**WRONG**:
```sql
-- ARRAY<JSON> is not supported
WITH parsed AS (
  SELECT CAST(json_extract(data, '$') AS ARRAY<JSON>) AS items
  FROM table_name
)
```

### JSON Extraction Patterns

| Use Case | Correct Pattern |
|----------|-----------------|
| Extract JSON array as strings | `CAST(json_extract_string(...) AS ARRAY<VARCHAR>)` |
| Extract array of IDs | `CAST(json_extract_string(...) AS ARRAY<VARCHAR>)` |
| Extract numeric array | `CAST(json_extract_string(...) AS ARRAY<DOUBLE>)` |
| Extract single JSON value | `json_extract_string(field, '$.key')` (no CAST needed) |
| No explicit cast needed | Use `json_extract` directly for basic access |

---

## Common Datasets

| Dataset | Purpose |
|---------|---------|
| `devrev.dim_ticket` | Support tickets |
| `devrev.dim_conversation` | Conversations |
| `devrev.dim_issue` | Engineering issues |
| `devrev.dim_account` | Customer accounts |
| `devrev.dim_revo` | RevOrgs (customer orgs) |
| `devrev.dim_devu` | DevUsers (internal users) |
| `devrev.dim_revu` | RevUsers (customer users) |
| `devrev.fact_engagement` | Engagement events |
