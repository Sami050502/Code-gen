# Data Assessment Guide

Assess actual data viability **before** finalizing widget specifications. Schema describes structure; data reveals reality.

## Purpose

Prevent widget generation failures caused by:
- Empty filter results (enum values differ from schema)
- Sparse fields (high NULL rates on grouping dimensions)
- Query timeouts (large fact tables without filters)
- Type mismatches (VARCHAR storing numbers)

## Assessment Workflow

### 1. Sample Each Unique Dataset

```bash
# Sample 20 rows to inspect actual values
dashboard-sync dataset query <dataset> --limit 20
```

### 2. Test Filter Conditions

For widgets with filters, verify they return data:

```bash
# Test specific filter conditions
dashboard-sync dataset query <dataset> --filter '{"field": "value"}' --limit 10
```

### 3. Check Field Characteristics

For each field used in a widget:
- **Enum fields**: Note actual values (case-sensitive)
- **Numeric fields**: Check for NULL rate and value ranges
- **Date fields**: Verify time range coverage
- **ID fields**: Confirm population for grouping

## Per-Widget Assessment Checks

| Check | Pass Criteria | Warn | Block |
|-------|---------------|------|-------|
| Field population | NULL rate < 50% | 50-80% NULL | >80% NULL |
| Enum values | Match filter values | Case mismatch | Empty result |
| Time range | Covers analysis period | Partial coverage | No data in range |
| Query feasibility | Returns in <5s | Slow response | Timeout |
| VARCHAR numeric | Detected and noted | TRY_CAST needed | - |

## Viability Classifications

### PASS
- All fields adequately populated
- Filter conditions return expected data
- Ready for widget generation

### WARN
- Issues detected but manageable
- Proceed with documented handling:
  - NULL handling strategy
  - Case normalization needed
  - Partial time coverage noted
- Widget generator receives context about issues

### BLOCK
- Critical data issues prevent widget from working
- Do NOT proceed with this widget
- Document alternative recommendations:
  - Different dataset
  - Different metric/dimension
  - Simplified version without problematic fields

## Assessment Output Format

Include in plan for each widget:

```markdown
#### Data Assessment
- **Viability:** PASS | WARN | BLOCK
- **Sample:** N rows from [dataset]
- **Fields assessed:**
  - `field_name`: N% populated, values: [actual values]
- **Filter test:** [condition] returns N rows
- **Risks:** [identified issues or "None"]
- **Notes:** [recommendations or "Ready for widget generation"]
```

## Summary Table

After all widget assessments, include summary:

```markdown
## Data Assessment Summary

| Widget | Dataset | Viability | Key Findings |
|--------|---------|-----------|--------------|
| 1. Name | dataset | PASS/WARN/BLOCK | Brief finding |

**Blocked:** N widgets (recommend alternatives)
**Warnings:** N widgets (handling documented)
```

## Common Issues and Resolutions

### High NULL Rate on Dimension Field

**Problem:** Grouping field has >50% NULL values
**Resolution:**
- WARN if 50-80%: Add COALESCE or filter out NULLs
- BLOCK if >80%: Recommend different dimension

### Enum Values Don't Match Schema

**Problem:** Schema says `['open', 'closed']` but data has `['Open', 'Closed', 'PENDING']`
**Resolution:**
- WARN: Document actual values for widget generator
- Use actual values in filter conditions

### Empty Filter Results

**Problem:** Filter condition returns 0 rows
**Resolution:**
- BLOCK: Cannot build meaningful widget
- Recommend looser filter or different dataset

### Time Range Gaps

**Problem:** Widget needs 90 days but data only has 60 days
**Resolution:**
- WARN: Adjust time range to available data
- Document coverage limitation

## Integration with Widget Generator

When a widget has WARN status, include the assessment details in the widget specification so the widget-generator agent can handle appropriately:

- NULL handling: "Use COALESCE(field, 'Unknown')"
- Case issues: "Actual enum values are uppercase"
- Sparse data: "Filter out NULL owner_id rows"
