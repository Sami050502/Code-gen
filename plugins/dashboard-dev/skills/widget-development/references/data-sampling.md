# Data Sampling Guide

**CRITICAL**: Schema metadata alone causes runtime failures. Always sample actual data before generating widgets.

## Why Sampling is Required

**Schema describes structure** (field names, types, descriptions)
**Data reveals reality** (actual values, NULL rates, distributions, edge cases)

**Runtime failures from schema-only approach**:
- Empty result sets (filter values don't match actual data)
- Query timeouts (unfiltered queries on large tables)
- NULL-dominated visualizations (sparse fields used for grouping)
- Type casting errors (unexpected data formats)
- JSON extraction failures (missing paths, null values)

## Sampling Workflow

### Step 1: Sample data structure (ALWAYS)

```bash
dashboard-sync dataset query <dataset> --limit 20
```

**What to check**:
- Field population: Count NULLs vs non-NULLs for key fields
- Actual enum values: May differ from schema (case, legacy values, custom)
- JSON structure: Verify paths exist, handle missing keys
- String formats: URLs, markdown, plain text (affects length aggregations)
- Array content: Check NULL, empty, populated distribution

### Step 2: Verify filter conditions (IF filtering)

```bash
dashboard-sync dataset query <dataset> --filter '{"priority": "p0"}' --limit 10
```

**What to check**:
- Returns data (not empty result)
- Actual values match filter (case-sensitive)
- Sufficient coverage (not <1% of data)

### Step 3: Check time range (IF time-series)

```bash
dashboard-sync dataset query <dataset> --limit 5
# Examine created_date, updated_date MIN/MAX in output
```

**What to check**:
- Date range covers expected period
- No unexpected gaps (data migration cutoffs)
- Sufficient history for rolling calculations (7-day average needs >7 days)

### Step 4: Assess table size (IF fact table or large dataset)

```bash
# Examine row count from sample query results
# Fact tables (>1M rows) REQUIRE filters to avoid timeout
```

**What to check**:
- Query executes within 1.5s timeout
- Mandatory filters needed (created_date range, account_id, etc.)

## Sample Analysis Checklist

Before generating widget JSON, verify:

- [ ] **Field population**: Critical fields have <50% NULL rate
- [ ] **Enum accuracy**: Use actual values from data, not schema assumptions
- [ ] **JSON path validity**: Paths exist in sample data, handle missing with COALESCE
- [ ] **Time range adequate**: Date fields cover expected analysis period
- [ ] **Query returns data**: Test conditions match actual rows (not empty set)
- [ ] **Foreign key coverage**: JOIN fields have >80% coverage (not sparse)
- [ ] **Array handling**: Check NULL/empty/populated distribution before operations
- [ ] **Performance viable**: Large tables have WHERE filters to prevent timeout
- [ ] **Distribution understood**: Check for outliers, skew in aggregations
- [ ] **ID validity**: ID fields reference existing entities (not orphaned)
- [ ] **VARCHAR numeric fields**: Identify fields that look numeric but are VARCHAR (quoted values, empty strings)

## Common Schema vs. Data Mismatches

| Schema Says | Data Shows | Widget Impact | Solution |
|-------------|------------|---------------|----------|
| `priority: enum ["p0", "p1"]` | `"P0", "CRITICAL", NULL` | Filter returns empty | Use actual values from sample |
| `account_id: id field` | 68% NULL | Grouped chart shows mostly NULL | Choose different dimension |
| `metadata: json field` | 60% missing `$.severity` | JSON extract fails | Use `COALESCE(json_extract(...), 'unknown')` |
| `created_date: timestamp` | MIN: 2024-03-15 (10 months) | 12-month filter partial | Adjust time range to available data |
| `response_time: double` | MAX: 86400 (24hr timeout) | AVG skewed by outliers | Use PERCENTILE_CONT instead of AVG |
| `tags: array` | 73% NULL or empty | Array[1] fails on most rows | Check `array_length()` before indexing |
| `parent_id: id` | 30% orphaned references | LEFT JOIN loses data | Add NULL handling or INNER JOIN |
| `fact_transitions: 45M rows` | Query timeout without filter | Unfiltered query fails | Add mandatory WHERE clause |

## Detecting VARCHAR Numeric Fields

VARCHAR fields containing numeric values are a common source of runtime errors. These fields look numeric in sample data but fail when cast or compared as numbers.

### How to Identify in Sample Output

| Observation | Indicates | Action |
|-------------|-----------|--------|
| Numeric values in quotes: `"123"`, `"45.6"` | VARCHAR type storing numbers | Use `TRY_CAST` with `COALESCE` |
| Empty string values: `""` | VARCHAR with missing data | Filter or provide default |
| Mixed values: `"100"`, `"N/A"`, `""` | VARCHAR with invalid entries | Use `TRY_CAST` to handle gracefully |
| Date-like strings: `"2024-01-15"` | VARCHAR date field | Use `TRY_CAST(x AS DATE)` |

### Sample Analysis Example

**Sample output showing VARCHAR numeric field:**
```json
{
  "rows": [
    {"id": "A-001", "view_count": "1523"},     // Quoted = VARCHAR
    {"id": "A-002", "view_count": ""},         // Empty string = problem for CAST
    {"id": "A-003", "view_count": "892"},
    {"id": "A-004", "view_count": null}        // NULL is handled by both CAST and TRY_CAST
  ]
}
```

**Analysis**: `view_count` is VARCHAR type (values are quoted). Contains empty strings.

**Solution**:
```sql
SELECT
  id,
  COALESCE(TRY_CAST(view_count AS BIGINT), 0) AS views
FROM devrev.dim_article
```

### Common VARCHAR Numeric Patterns

| Field Pattern | Typical Source | Handling |
|---------------|----------------|----------|
| View/read counts | Analytics import | `COALESCE(TRY_CAST(x AS BIGINT), 0)` |
| Duration/time values | External system sync | `TRY_CAST(x AS BIGINT)` with filter |
| Score/rating fields | User input | `TRY_CAST(x AS DOUBLE)` |
| Version numbers | String versioning | Keep as VARCHAR or parse segments |

**See also**: `references/sql-patterns.md` → "Safe Type Conversion with TRY_CAST"

## Output Location

Query results saved to:
```
datasets/queries/<dataset>_query.json
```

Format: JSON with `{"dataset": "...", "query": "...", "rows": [...]}`

Read this file to analyze sample data before generating widget.

## Example Analysis Workflow

### Example 1: Ticket Status Distribution

**Requirements**: Show ticket count by status

**Step 1: Sample dim_ticket**
```bash
dashboard-sync dataset query devrev.dim_ticket --limit 20
```

**Analysis**:
```json
{
  "rows": [
    {"id": "T-001", "status": "open", "priority": "p1"},
    {"id": "T-002", "status": "OPEN", "priority": "P1"},  // ⚠️ Case mismatch
    {"id": "T-003", "status": "closed", "priority": null},  // ⚠️ NULL priority
    ...
  ]
}
```

**Findings**:
- Status has mixed case: "open", "OPEN", "closed", "CLOSED"
- Priority has ~15% NULL values
- Need to normalize case or use actual values as-is

**Decision**: Use lowercase values in SQL with `LOWER(status)` for consistency

### Example 2: Response Time P90

**Requirements**: Show P90 response time for last 7 days

**Step 1: Sample fact_api_request**
```bash
dashboard-sync dataset query devrev.fact_api_request --limit 20
```

**Analysis**:
```json
{
  "rows": [
    {"response_time_ms": 125, "date": "2024-01-20"},
    {"response_time_ms": 2300, "date": "2024-01-21"},
    {"response_time_ms": 86400000, "date": "2024-01-22"},  // ⚠️ 24 hour timeout!
    ...
  ]
}
```

**Findings**:
- Response times include outliers (timeouts > 60 seconds)
- MAX value: 86,400,000 ms (24 hours)
- Date range: 2023-06-01 to 2024-01-28 (sufficient history)

**Decision**:
1. Filter out timeouts: `WHERE response_time_ms < 60000` (< 1 minute)
2. Use P90 instead of AVG to handle remaining outliers
3. Add date filter: `WHERE date >= CURRENT_DATE - INTERVAL '7 days'`

### Example 3: JSON Metadata Extraction

**Requirements**: Show severity distribution from metadata JSON field

**Step 1: Sample tickets with metadata**
```bash
dashboard-sync dataset query devrev.dim_ticket --limit 20
```

**Analysis**:
```json
{
  "rows": [
    {"metadata": {"severity": "high", "source": "api"}},
    {"metadata": {"source": "web"}},  // ⚠️ Missing severity key
    {"metadata": null},  // ⚠️ NULL metadata
    ...
  ]
}
```

**Findings**:
- 40% have metadata.severity
- 25% have metadata but no severity key
- 35% have NULL metadata
- Severity values: "high", "medium", "low"

**Decision**:
1. Use `COALESCE(json_extract(metadata, '$.severity'), 'unknown')` to handle missing
2. Group by severity including "unknown" category
3. Consider filtering to only rows with severity if "unknown" dominates

## Tips for Large Tables

**Fact tables** (fact_transitions, fact_api_request, fact_events):
- Always add date filter: `WHERE date >= CURRENT_DATE - INTERVAL '30 days'`
- Consider account_id filter if analyzing single account
- Sample with `--limit 10` first to check structure

**Dimension tables** (dim_ticket, dim_account, dim_work):
- Usually safe to query without filters
- Check for is_deleted field and filter to `WHERE is_deleted = false`
- Sample with `--limit 50` to see value distributions

## Handling NULL Values

### NULL in Dimensions

If dimension has high NULL rate (>30%), consider:
1. Use `COALESCE(column, 'Unknown')` to show as category
2. Filter out NULLs with `WHERE column IS NOT NULL`
3. Choose a different dimension with better coverage

### NULL in Measures

If measure source has NULLs:
1. Use aggregate functions that ignore NULLs (COUNT, SUM, AVG)
2. Or use `COALESCE(column, 0)` before aggregation
3. Be aware COUNT(*) includes NULLs, COUNT(column) excludes them

## Performance Guidelines

| Table Size | Filter Required | Typical Timeout Risk |
|------------|-----------------|---------------------|
| < 10K rows | Optional | Low |
| 10K - 100K rows | Recommended | Medium |
| 100K - 1M rows | Required | High |
| > 1M rows | Mandatory | Very High |

**Rule**: For tables >100K rows, always add WHERE clause with indexed fields (date, account_id, status).
