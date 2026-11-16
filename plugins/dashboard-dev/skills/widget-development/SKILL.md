---
name: widget-development
description: This skill should be used when the user asks to "create a widget", "make a chart", "generate widget JSON", "fix widget error", "debug widget validation", "create a visualization", "write OASIS SQL", "define Meerkat aggregations", "add measures or dimensions", or mentions widget-related tasks for DevRev dashboards including two-layer architecture, data sampling, or field schema.
---

# Widget Development

Generate DevRev dashboard widgets with OASIS SQL queries and Meerkat aggregations.

## Overview

DevRev widgets combine SQL queries (OASIS layer) with aggregation logic (Meerkat layer) to create interactive visualizations. The two-layer architecture separates data extraction from aggregation, enabling efficient query execution and flexible visualization.

**Core workflow**:
1. Sample dataset to understand actual data (MANDATORY)
2. Write OASIS SQL query to extract raw data
3. Define dimensions (grouping fields) and measures (aggregated values)
4. Configure visualization (chart type, axes, colors)
5. Validate using 3-stage pipeline (Structure → Semantic → API)

## Execution Context

**SQL Dialect**: DuckDB - Use DuckDB syntax and functions in OASIS queries.

**Runtime Constraints**:
- 1,000 row limit (automatic)
- 1.5 second timeout (optimize queries if timing out)
- Queries execute via QuackQL engine

**Architecture**: Two-layer model where OASIS extracts data, Meerkat aggregates it.

## Critical: Two-Layer Architecture

DevRev uses a **two-layer query model**. Understanding this is critical to avoid runtime errors.

| Layer | Location | Purpose | Allowed Operations |
|-------|----------|---------|-------------------|
| **OASIS** | `oasis.sql_query` | Raw data extraction | SELECT, JOIN, WHERE, CTE, JSON extraction, CAST, CASE, NULLIF, COALESCE |
| **Meerkat** | `meerkat_schema.sql_expression` | Aggregations only | Column references, arithmetic, aggregate functions (COUNT, SUM, AVG), window functions (OVER) |

**Hard Rules**:
1. Window functions (`OVER`) MUST be in Meerkat, never in OASIS
2. Complex SQL functions (NULLIF, CAST, CASE) MUST be in OASIS, never in Meerkat
3. Every measure MUST use an aggregate function (after GROUP BY, only dimensions and aggregated values exist)

### Meerkat Formula-Only Syntax

Meerkat `sql_expression` supports **formula syntax only**, not full SQL.

❌ **Never use in Meerkat**: `NULLIF()`, `CAST()`, `CASE WHEN`, `COALESCE()`
✅ **Only use in Meerkat**: Column references, arithmetic, aggregate functions, window functions

**Why**: Meerkat evaluates expressions AFTER data aggregation. Move complex logic to OASIS.

**Common pattern** - Pre-compute complex logic in OASIS:
```json
{
  "oasis": {
    "sql_query": "SELECT NULLIF(duration, 0) AS clean_duration FROM tickets"
  },
  "measures": [{
    "sql_expression": "AVG(clean_duration)"  // Simple formula in Meerkat
  }]
}
```

See `references/meerkat-constraints.md` for detailed patterns and examples.

### Measure Aggregation Requirement

**Every measure MUST use an aggregate function**. After Meerkat applies GROUP BY, only dimension columns exist.

❌ **Wrong**: `"sql_expression": "revenue"` (fails with "column must appear in GROUP BY")
✅ **Correct**: `"sql_expression": "SUM(revenue)"` (aggregated)

**Valid aggregate functions**: COUNT, SUM, AVG, MIN, MAX, MEDIAN (via function.type), percentiles (via function.type)

### Percentile Functions

Use `function.type` enum, **NOT** SQL functions like `PERCENTILE_CONT()`.

❌ **Wrong**: `"sql_expression": "PERCENTILE_CONT(0.9) WITHIN GROUP (ORDER BY time)"`
✅ **Correct**: `"function": {"type": "MeerkatWidgetColumnFunction_TypeEnumP90"}` + `"sql_expression": "time"`

**Available enums**: P50, P90, P95, P99, Median

See `references/meerkat-constraints.md` → "Percentile Functions" for complete examples.

## Widget Structure

Basic widget JSON structure:

```json
{
  "version": "v0",
  "name": "unique-widget-name",
  "title": "Widget Title",
  "description": "What this widget displays",
  "data_sources": [{
    "reference_name": "data",
    "type": "oasis",
    "oasis": {
      "datasets": ["devrev.dim_ticket"],
      "sql_query": "SELECT id, priority FROM devrev.dim_ticket WHERE is_deleted = false"
    },
    "dimensions": [...],
    "measures": [...]
  }],
  "sub_widgets": [{
    "reference_id": "chart1",
    "query": {
      "dimensions": ["data.priority"],
      "measures": ["data.count"]
    },
    "visualization": {
      "type": "line",
      "line": {
        "x": [{"reference_name": "data.date", "label": "Date"}],
        "y": [{"reference_name": "data.count", "label": "Count"}]
      }
    }
  }],
  "layout": [{"position": {"height": 3, "width": 6, "x": 0, "y": 0}, "reference_id": "chart1"}]
}
```

**Required fields:**
- `"version": "v0"` - Without this, defaults to v1 (requires different data source type)
- `"name"` - Unique identifier (lowercase, underscores allowed, no hyphens/dots)
- `"title"` - Display title shown in UI
- `"description"` - Brief description of widget purpose
- `layout` array - Without this, widget renders blank with no error
- `data_sources` array - At least one data source required
- `sub_widgets` array - At least one sub-widget required

## Data Sampling (MANDATORY Before Widget Generation)

**CRITICAL**: Schema metadata alone causes runtime failures. Always sample actual data first.

**Why**: Schema describes structure, data reveals reality (actual values, NULL rates, distributions, edge cases).

**Sampling workflow**:

1. **Sample data structure** (ALWAYS):
   ```bash
   dashboard-sync dataset query <dataset> --limit 20
   ```
   Check: Field population, actual enum values, JSON structure, array content

2. **Verify filter conditions** (IF filtering):
   ```bash
   dashboard-sync dataset query <dataset> --filter '{"status": "open"}' --limit 10
   ```
   Check: Returns data, values match filter (case-sensitive)

3. **Check time range** (IF time-series):
   Examine created_date, updated_date MIN/MAX in output
   Check: Date range covers expected period, sufficient history

4. **Assess table size** (IF fact table):
   Check: Query executes within 1.5s timeout
   Action: Add WHERE clause for large tables (>100K rows)

**Output location**: `datasets/queries/<dataset>_query.json`

See `references/data-sampling.md` for detailed checklist and common mismatches.

## Field Schema

Dimensions and measures require specific field structure:

```json
{
  "reference_name": "field_name",
  "devrev_schema": {
    "field_type": "text",           // text, int, double, enum, id, timestamp
    "is_filterable": true,          // true for dimensions, false for measures
    "ui": {"display_name": "Label"}
  },
  "meerkat_schema": {
    "type": "string",  // Use: string, number, time, boolean, string_array, number_array
    "sql_expression": "field_name"  // Required for measures, optional for dimensions
  }
}
```

**Common mistakes**:
- ❌ `display_name` at root level → ✅ Put inside `devrev_schema.ui`
- ❌ `type` in devrev_schema → ✅ Use `field_type`
- ❌ `direction: "desc"` → ✅ Use `"descending"` or `"ascending"`

**Type mappings** (devrev_schema.field_type → meerkat_schema.type):
- `text`, `enum`, `id`, `tokens` → `string`
- `int`, `double` → `number`
- `timestamp`, `date` → `time`
- `bool` → `boolean`
- `[]id`, `[]text`, `[]enum` → `string_array`
- `[]int`, `[]double` → `number_array`

See `references/field-schema.md` for complete structure and examples.

## Visualization

Charts require `x` and `y` as arrays of objects:

```json
"line": {
  "x": [{"reference_name": "data.date", "label": "Date"}],
  "y": [{
    "reference_name": "data.count",
    "label": "Count",
    "color": {"type": "static", "static": "chart-category-1-base"}
  }]
}
```

**Color values**: `chart-category-1-base` through `chart-category-10-base`

### Donut/Pie Asymmetry

**CRITICAL**: Donut and pie have asymmetric structure - `x` is array, `y` is object (not array).

✅ **Correct**:
```json
"donut": {
  "x": [{"reference_name": "data.category", "label": "Category"}],  // Array
  "y": {"reference_name": "data.count", "label": "Count"}  // Object
}
```

### Metric Visualization

For single KPI values, `metric.y` is an **array**:

✅ **Correct**:
```json
"metric": {
  "y": [{"reference_name": "data.kpi_value", "label": "KPI"}]  // Array
}
```

See `references/visualization-patterns.md` for all chart types and patterns.

## SQL Constraints

**Array type syntax**: Use `ARRAY<TYPE>`, not `TYPE[]`
- ✅ `CAST(json_extract(data, '$') AS ARRAY<JSON>)`
- ❌ `CAST(json_extract(data, '$') AS JSON[])`

**CAST types**: Use `BIGINT` (not INTEGER), `DOUBLE` (not FLOAT)
- ✅ `CAST(count AS BIGINT)`
- ❌ `CAST(count AS INTEGER)`

**Table format**: Always use `devrev.` prefix
- ✅ `FROM devrev.dim_ticket`
- ❌ `FROM dim_ticket`

**Performance**: Fact tables (>1M rows) REQUIRE date filters to avoid timeout

See `references/sql-patterns.md` for detailed constraints and patterns.

## Validation

Validate widgets using the 3-stage pipeline:

```bash
dashboard-sync widget validate widgets/<name>.json
```

**Three stages**:
1. **Structure** - JSON schema validation (must pass)
2. **Semantic** - Business rules (SQL syntax, type mappings, enum values)
3. **API** - Platform validation (final authority)

Hooks automatically trigger validation when widget files are written.

## References

### Core Documentation

| File | Content |
|------|---------|
| `templates.yaml` | Dimension/measure templates, ID types, dataset names |
| `validation-schema.yaml` | Type mappings, visualization fields, enum values |
| `quick-reference.md` | Widget JSON structure, chart formats |
| `errors.md` | Error diagnosis and debugging commands |

### Detailed References

Load these for specific topics:

| File | When to Load |
|------|-------------|
| **`references/meerkat-constraints.md`** | Two-layer architecture, formula syntax, percentile patterns, window functions |
| **`references/sql-patterns.md`** | DuckDB syntax, CAST types, array syntax, JOIN limitations, performance optimization |
| **`references/field-schema.md`** | Complete field structure, type mappings, aggregate function enums, common mistakes |
| **`references/visualization-patterns.md`** | All chart types, donut/pie asymmetry, metric cards, color configuration |
| **`references/data-sampling.md`** | Sampling workflow, analysis checklist, schema vs. data mismatches, handling NULLs |

**Usage pattern**: Start with this SKILL.md for core workflow. When encountering specific issues or needing detailed patterns, load the relevant reference file.

## Common Pitfalls

1. **Skipping data sampling** → Always sample before generating widgets
2. **Complex functions in Meerkat** → Move NULLIF, CAST, CASE to OASIS
3. **Direct column reference in measures** → Use aggregate functions (SUM, AVG, COUNT)
4. **PERCENTILE_CONT() in Meerkat** → Use function.type enum instead
5. **Wrong CAST types** → Use BIGINT (not INTEGER), DOUBLE (not FLOAT)
6. **Donut y as array** → Use single object for y (asymmetric structure)
7. **Missing version field** → Add `"version": "v0"` to avoid v1 default
8. **No layout array** → Widget renders blank without layout
9. **CAST on VARCHAR numeric fields** → Use `TRY_CAST` with `COALESCE` for safe conversion (see `references/sql-patterns.md`)
10. **is_filterable on VARCHAR date fields** → Set `false` to prevent Meerkat auto-filter type mismatch (see `references/field-schema.md`)
11. **Not detecting VARCHAR numeric fields** → Check if numeric values are quoted in samples (see `references/data-sampling.md`)
12. **Missing `name` field error** → Add `devrev_schema.{name, data_name, db_name}` (all equal `reference_name`) in ALL measures/dimensions (see `references/field-schema.md`)

## Getting Started

**Step-by-step widget creation**:

1. **Identify dataset**: Determine which table(s) contain required data
2. **Fetch schema**: `dashboard-sync dataset fetch <dataset>`
3. **Sample data**: `dashboard-sync dataset query <dataset> --limit 20`
4. **Analyze sample**: Check NULL rates, enum values, date ranges, distributions
5. **Write OASIS query**: SELECT statement with JOINs, WHERE filters, CAST/CASE logic
6. **Define dimensions**: Grouping fields with proper devrev_schema and meerkat_schema
7. **Define measures**: Aggregated metrics using SUM, AVG, COUNT, percentiles
8. **Configure visualization**: Choose chart type, map dimensions/measures to x/y axes
9. **Add layout**: Position and size in 12-column grid
10. **Validate**: Automatic validation via hooks or manual via CLI

**For detailed patterns on each step**, consult the reference files listed above.
