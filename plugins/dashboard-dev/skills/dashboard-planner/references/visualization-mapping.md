# Field-to-Visualization Mapping

Conceptual guidance for selecting appropriate widget types based on schema field characteristics.

**Technical authority:** For field type validation, type mappings, and SQL patterns, see `widget-development` skill.

## Quick Decision Guide

```
What question are you answering?
    │
    ├─► "How many X?" ────────────────► metric
    ├─► "X over time?" ───────────────► line
    ├─► "X by category?" ─────────────► bar
    ├─► "What % of X?" ───────────────► donut
    └─► "Show me details of X?" ──────► table
```

## Schema Field Analysis

When reading schema files, identify field purposes:

### Timestamp Fields
**Schema patterns:** `*_date`, `*_at`, `created_date`, `modified_date`
**Schema type:** `TIMESTAMP` or `DATE`

**Planning use:**
- Line chart X-axis (aggregate by day/week/month)
- Time range filters
- Trend analysis

### Enum Fields
**Schema indicator:** `value_set` with `cardinality` and `enum_values`

**Planning use based on cardinality:**
- **< 10 values** → Bar or donut dimension
- **10-50 values** → Bar with potential filter
- **> 50 values** → Consider table instead

**Example from schema:**
```yaml
name: priority
type: VARCHAR
value_set:
  cardinality: 4
  enum_values:
    - {value: "blocker", ordinal: 1}
    - {value: "high", ordinal: 2}
    - {value: "medium", ordinal: 3}
    - {value: "low", ordinal: 4}
```
→ Low cardinality (4), good for bar chart dimension

### Numeric Fields
**Schema patterns:** `*_count`, `*_total`, `*_hours`, `*_days`
**Schema type:** `BIGINT`, `INTEGER`, `DOUBLE`, `FLOAT`

**Planning use:**
- Metric widgets (single value display)
- Y-axis measures (with aggregation)
- Threshold-based filtering

### ID Fields
**Schema patterns:** `*_id`, `id`

**Planning use:**
- COUNT DISTINCT for unique counts
- Grouping dimension (with lookup)
- NOT for direct display (use joined name instead)

### Boolean Fields
**Schema type:** `BOOLEAN`

**Planning use:**
- Binary split visualization (donut)
- Filter condition
- Percentage calculation

## Widget Type by Data Shape

| Data Shape | Widget | Typical Schema Fields |
|------------|--------|----------------------|
| Single aggregate | metric | COUNT(*), SUM(numeric_field) |
| Time series | line | timestamp + aggregate |
| Categorical breakdown | bar | enum + COUNT(*) |
| Part-of-whole | donut | enum + COUNT(*) |
| Multi-column detail | table | Multiple fields |

## Business Question Patterns

### "How many open tickets?"
```
Widget: metric
Dataset: dim_ticket
Fields: status (enum), id (for COUNT)
Measure: COUNT(*) WHERE status IN ('open', 'in_progress')
```

### "Tickets created over time?"
```
Widget: line
Dataset: dim_ticket
Fields: created_date (timestamp), id (for COUNT)
X-axis: created_date (weekly aggregation)
Y-axis: COUNT(*)
```

### "Tickets by priority?"
```
Widget: bar
Dataset: dim_ticket
Fields: priority (enum, 4 values), id (for COUNT)
Dimension: priority
Measure: COUNT(*)
```

### "Status distribution?"
```
Widget: donut
Dataset: dim_ticket
Fields: status (enum), id (for COUNT)
Dimension: status
Measure: COUNT(*)
```

## Aggregation Selection

| Time Span | Recommended Aggregation |
|-----------|------------------------|
| < 7 days | hourly or daily |
| 1-4 weeks | daily |
| 1-3 months | weekly |
| 3-12 months | weekly or monthly |
| > 1 year | monthly |

## What NOT to Include in Plans

Plans focus on WHAT to build. These technical details are for widget-development:

- Exact SQL expressions
- Meerkat type mappings
- Field schema JSON structure
- Visualization array configuration
- Two-layer architecture details

## Cross-Reference

For technical implementation after planning:
- **Field types and mappings** → `widget-development` skill
- **SQL patterns** → `widget-development/references/sql-constraints.md`
- **Dashboard layout** → `dashboard-development` skill
