# Plan Output Format

Plans use simple, human-readable Markdown. No YAML frontmatter needed - models can infer structure from well-organized content.

## Location

All plans go to `plans/` folder:
```
plans/
├── support-team.md
├── customer-health.md
└── product-velocity.md
```

## Template

```markdown
# Dashboard: [Title]

## Purpose

[1-2 sentences describing the dashboard's goal and audience]

## Widgets

### 1. [Widget Name]
- **Type:** metric | line | bar | donut | table
- **Dataset:** devrev.[dataset_name]
- **Measure:** [aggregation expression]
- **Dimension:** [grouping field] (if applicable)
- **Filter:** [condition] (if applicable)
- **Rationale:** [Why this widget answers a business question]

### 2. [Widget Name]
...

## Organization

| Tab | Widgets | Purpose |
|-----|---------|---------|
| [Tab Name] | 1, 2, ... | [Brief description] |

## Assumptions

1. [Assumption about data interpretation]
2. [Assumption about time ranges]
3. [Assumption about filters]
```

## Section Guidelines

### Purpose
- One sentence on WHAT the dashboard shows
- One sentence on WHO uses it

### Widgets
Each widget needs:
- **Type** - One of: metric, line, bar, column, donut, table
- **Dataset** - Full name with `devrev.` prefix
- **Measure** - What to calculate (COUNT, SUM, AVG, etc.)
- **Dimension** - How to group (only for bar/line/donut)
- **Filter** - Data restrictions (optional)
- **Rationale** - Business justification

### Organization
- Group related widgets into tabs
- Maximum 50 widgets per tab (platform limit)
- Use clear tab names (Overview, Trends, Details)

### Assumptions
Document decisions made during planning:
- How ambiguous terms are interpreted
- Default time ranges
- Filter inclusions/exclusions
- Enum value interpretations

## Data Assessment Section

Each widget specification should include an assessment block:

```markdown
### [Widget Name]
- **Type:** ...
- **Dataset:** ...
- **Measure:** ...
- **Rationale:** ...

#### Data Assessment
- **Viability:** PASS | WARN | BLOCK
- **Sample:** N rows from [dataset]
- **Fields assessed:**
  - `field_name`: N% populated, values: [actual values]
- **Filter test:** [condition] returns N rows
- **Risks:** [identified issues or "None"]
- **Notes:** [recommendations or "Ready for widget generation"]
```

## Assessment Summary Table

Add before Assumptions section:

```markdown
## Data Assessment Summary

| Widget | Dataset | Viability | Key Findings |
|--------|---------|-----------|--------------|
| 1. Name | dataset | PASS/WARN/BLOCK | Brief finding |

**Blocked:** N widgets (recommend alternatives)
**Warnings:** N widgets (handling documented)
```

## Example: Support Dashboard

```markdown
# Dashboard: Support Team Performance

## Purpose

Monitor support ticket health and team efficiency. Used by support managers for daily standups and capacity planning.

## Widgets

### 1. Open Tickets
- **Type:** metric
- **Dataset:** devrev.dim_ticket
- **Measure:** COUNT(*) WHERE status IN ('open', 'in_progress')
- **Rationale:** Shows current workload at a glance

### 2. Resolution Time Trend
- **Type:** line
- **Dataset:** devrev.fact_ticket_stage_transitions
- **Measure:** AVG(time_in_stage_hours)
- **Dimension:** transition_date (weekly)
- **Filter:** stage_type = 'resolved', last 90 days
- **Rationale:** Track team efficiency over time

### 3. Tickets by Priority
- **Type:** bar
- **Dataset:** devrev.dim_ticket
- **Measure:** COUNT(*)
- **Dimension:** priority
- **Filter:** status != 'closed'
- **Rationale:** Understand severity distribution

### 4. Tickets by Owner
- **Type:** table
- **Dataset:** devrev.dim_ticket
- **Columns:** owner_name, open_count, in_progress_count, avg_age_days
- **Filter:** status != 'closed'
- **Rationale:** Workload distribution across team

## Organization

| Tab | Widgets | Purpose |
|-----|---------|---------|
| Overview | 1, 2, 3 | Quick health check |
| Team | 4 | Capacity planning |

## Assumptions

1. "Open" includes both 'open' and 'in_progress' status values
2. Resolution time measured from 'resolved' stage transitions only
3. Weekly aggregation for trend charts (balances detail vs. noise)
4. Last 90 days for trends (quarterly view)
```

## What Plans Do NOT Include

Plans are conceptual. These technical details are handled during implementation:

| NOT in Plan | Where It's Handled |
|-------------|-------------------|
| JSON structure | widget-development, dashboard-development |
| SQL expressions | widget-development |
| Field schema format | widget-development |
| Grid positions | dashboard-development |
| Meerkat type mappings | widget-development |

## Validation Checklist

Before finalizing a plan, verify:

- [ ] Each widget has Type, Dataset, and Measure
- [ ] Datasets are prefixed with `devrev.`
- [ ] Enum dimensions note cardinality when relevant
- [ ] Time dimensions specify aggregation level
- [ ] Organization table accounts for all widgets
- [ ] Assumptions document interpretation decisions

## Tips

- Keep plans focused on WHAT, not HOW
- Use natural language for measures (not exact SQL)
- Reference schema enum values when known
- Document assumptions even if they seem obvious
- One plan file per dashboard
