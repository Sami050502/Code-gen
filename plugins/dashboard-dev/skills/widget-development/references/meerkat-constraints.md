# Meerkat Layer Constraints

Detailed constraints, patterns, and rules for the Meerkat aggregation layer.

## Two-Layer Architecture

DevRev uses a **two-layer query model**. Understanding this architecture is critical to avoid runtime errors.

| Layer | Location | Purpose | Allowed |
|-------|----------|---------|---------|
| **OASIS** | `oasis.sql_query` | Raw data extraction | SELECT, JOIN, WHERE, CTE, JSON extraction, CAST, CASE, NULLIF |
| **Meerkat** | `meerkat_schema.sql_expression` | Aggregations only | Column references, arithmetic, aggregate functions, window functions |

**Hard Rule**: Window functions (`OVER`) MUST be in Meerkat, never in OASIS.

**Hard Rule**: Complex SQL functions (NULLIF, CAST, CASE) MUST be in OASIS, never in Meerkat.

## Meerkat sql_expression is Formula-Only

**CRITICAL**: Meerkat `sql_expression` fields support **formula syntax only**, not full SQL.

❌ **NEVER use these in Meerkat sql_expression**:
- `NULLIF()` - Conditional null handling
- `CAST()` - Type conversions
- `CASE WHEN ... THEN ... END` - Conditional logic
- `COALESCE()` - Null coalescing
- Any complex SQL function

✅ **ONLY use these in Meerkat sql_expression**:
- Column references: `column_name`
- Arithmetic: `column1 + column2`, `column1 * 100`
- Aggregate functions: `SUM(column)`, `AVG(column)`, `COUNT(column)`
- Window functions: `SUM(column) OVER (PARTITION BY ...)`

**Why**: Meerkat expressions are evaluated AFTER data aggregation. Complex SQL logic must be in the OASIS layer.

**Error you'll see if violated**:
```
Function 'NULLIF' not supported in Meerkat measure expressions
Function 'CAST' not supported in Meerkat measure expressions
Function 'CASE' not supported in Meerkat measure expressions
```

**Solution**: Move complex logic to OASIS `sql_query`.

### Example: NULLIF Pattern

❌ **WRONG** - NULLIF in Meerkat:
```json
{
  "oasis": {
    "sql_query": "SELECT duration FROM tickets"
  },
  "measures": [{
    "sql_expression": "AVG(NULLIF(duration, 0))"  // ❌ ERROR
  }]
}
```

✅ **CORRECT** - Pre-compute in OASIS:
```json
{
  "oasis": {
    "sql_query": "SELECT NULLIF(duration, 0) AS clean_duration FROM tickets"
  },
  "measures": [{
    "sql_expression": "AVG(clean_duration)"  // ✓ Simple formula
  }]
}
```

### Example: CAST Pattern

❌ **WRONG** - CAST in Meerkat:
```json
{
  "oasis": {
    "sql_query": "SELECT priority FROM tickets"
  },
  "measures": [{
    "sql_expression": "AVG(CAST(priority AS DOUBLE))"  // ❌ ERROR
  }]
}
```

✅ **CORRECT** - Pre-compute in OASIS:
```json
{
  "oasis": {
    "sql_query": "SELECT CAST(priority AS DOUBLE) AS priority_num FROM tickets"
  },
  "measures": [{
    "sql_expression": "AVG(priority_num)"  // ✓ Simple formula
  }]
}
```

### Example: CASE WHEN Pattern

❌ **WRONG** - CASE in Meerkat:
```json
{
  "oasis": {
    "sql_query": "SELECT status FROM tickets"
  },
  "measures": [{
    "sql_expression": "COUNT(CASE WHEN status = 'closed' THEN 1 END)"  // ❌ ERROR
  }]
}
```

✅ **CORRECT** - Pre-compute in OASIS:
```json
{
  "oasis": {
    "sql_query": "SELECT CASE WHEN status = 'closed' THEN 1 ELSE 0 END AS is_closed FROM tickets"
  },
  "measures": [{
    "sql_expression": "SUM(is_closed)"  // ✓ Simple formula
  }]
}
```

## Measure Aggregation Requirement

**CRITICAL**: Every measure MUST use an aggregate function. After Meerkat applies GROUP BY (using all dimensions), only dimension columns and aggregated values exist.

❌ **WRONG** - Direct column reference fails:
```json
{
  "dimensions": [{"reference_name": "product"}],
  "measures": [{
    "reference_name": "revenue",
    "sql_expression": "revenue"  // ❌ ERROR: column "revenue" must appear in GROUP BY
  }]
}
```

✅ **CORRECT** - Use aggregate function:
```json
{
  "dimensions": [{"reference_name": "product"}],
  "measures": [{
    "reference_name": "total_revenue",
    "sql_expression": "SUM(revenue)"  // ✓ Aggregated
  }]
}
```

**Valid aggregate functions**:
- `COUNT(*)` - Count rows
- `COUNT(column)` - Count non-NULL values
- `COUNT(DISTINCT column)` - Count unique values
- `SUM(column)` - Sum values
- `AVG(column)` - Average values
- `MIN(column)` - Minimum value
- `MAX(column)` - Maximum value
- `MEDIAN(column)` - Median value (via function.type enum)
- Percentiles: P50, P90, P95, P99 (via function.type enum)

**Rule**: If you're referencing a column from OASIS in a measure, it MUST be inside an aggregate function.

## Percentile Functions - Use function.type Enum

**CRITICAL**: Percentile calculations in Meerkat use `function.type` enum, **NOT** SQL functions like `PERCENTILE_CONT()`.

❌ **WRONG** - SQL function syntax:
```json
{
  "measures": [{
    "reference_name": "p90_response_time",
    "meerkat_schema": {
      "type": "number",
      "sql_expression": "PERCENTILE_CONT(0.9) WITHIN GROUP (ORDER BY response_time)"  // ❌ ERROR
    }
  }]
}
```

**Error you'll see**:
```
Function 'PERCENTILE_CONT' not supported in Meerkat measure expressions
```

✅ **CORRECT** - Use function.type enum:
```json
{
  "measures": [{
    "reference_name": "p90_response_time",
    "devrev_schema": {
      "field_type": "number",
      "ui": {"display_name": "P90 Response Time"}
    },
    "meerkat_schema": {
      "type": "number",
      "function": {
        "type": "MeerkatWidgetColumnFunction_TypeEnumP90"
      },
      "sql_expression": "response_time"  // ✓ Simple column reference
    }
  }]
}
```

**Available percentile enums**:
- `MeerkatWidgetColumnFunction_TypeEnumP50` - Median (50th percentile)
- `MeerkatWidgetColumnFunction_TypeEnumP90` - 90th percentile
- `MeerkatWidgetColumnFunction_TypeEnumP95` - 95th percentile
- `MeerkatWidgetColumnFunction_TypeEnumP99` - 99th percentile
- `MeerkatWidgetColumnFunction_TypeEnumMedian` - Median (alias for P50)

**Rule**: For percentile calculations:
1. Set `function.type` to the appropriate enum
2. Use simple column reference in `sql_expression`
3. Meerkat automatically applies the percentile aggregation

**Complete example** - P90, P95, P99 response times:
```json
{
  "data_sources": [{
    "reference_name": "data",
    "type": "oasis",
    "oasis": {
      "datasets": ["devrev.fact_api_request"],
      "sql_query": "SELECT response_time_ms FROM devrev.fact_api_request WHERE date >= CURRENT_DATE - INTERVAL '7 days'"
    },
    "measures": [
      {
        "reference_name": "p90_response",
        "devrev_schema": {
          "field_type": "number",
          "ui": {"display_name": "P90 Response Time (ms)"}
        },
        "meerkat_schema": {
          "type": "number",
          "function": {
            "type": "MeerkatWidgetColumnFunction_TypeEnumP90"
          },
          "sql_expression": "response_time_ms"
        }
      },
      {
        "reference_name": "p95_response",
        "devrev_schema": {
          "field_type": "number",
          "ui": {"display_name": "P95 Response Time (ms)"}
        },
        "meerkat_schema": {
          "type": "number",
          "function": {
            "type": "MeerkatWidgetColumnFunction_TypeEnumP95"
          },
          "sql_expression": "response_time_ms"
        }
      },
      {
        "reference_name": "median_response",
        "devrev_schema": {
          "field_type": "number",
          "ui": {"display_name": "Median Response Time (ms)"}
        },
        "meerkat_schema": {
          "type": "number",
          "function": {
            "type": "MeerkatWidgetColumnFunction_TypeEnumMedian"
          },
          "sql_expression": "response_time_ms"
        }
      }
    ]
  }]
}
```

## {MEERKAT} Placeholder

The `{MEERKAT}` prefix is **only valid inside OVER() clauses** for referencing aggregated dimensions:

✅ **CORRECT** - Inside OVER():
```sql
AVG(COUNT(*)) OVER (ORDER BY {MEERKAT}.created_date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW)
```

❌ **WRONG** - Outside OVER() causes parser error:
```sql
DATE_TRUNC('day', {MEERKAT}.created_date)
```

**Why**: The `{MEERKAT}` prefix references columns after aggregation. Only window function OVER clauses can reference these aggregated columns.

**Rule**: Use `{MEERKAT}.column_name` only in OVER() partition/order clauses.

## Window Functions

Window functions (`OVER` clause) MUST be in Meerkat, never in OASIS.

✅ **CORRECT** - Window function in Meerkat:
```json
{
  "oasis": {
    "sql_query": "SELECT created_date, ticket_count FROM devrev.dim_ticket"
  },
  "measures": [{
    "sql_expression": "AVG(COUNT(*)) OVER (ORDER BY {MEERKAT}.created_date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW)"
  }]
}
```

❌ **WRONG** - Window function in OASIS:
```sql
SELECT
  created_date,
  AVG(ticket_count) OVER (ORDER BY created_date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW)  -- ❌ ERROR
FROM devrev.dim_ticket
```

**Rule**: All window functions with OVER() must be in meerkat_schema.sql_expression, not in oasis.sql_query.
