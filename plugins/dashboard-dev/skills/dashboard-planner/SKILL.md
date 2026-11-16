---
name: dashboard-planner
description: This skill should be used when the user asks to "plan a dashboard", "help me design a dashboard", "what visualizations should I use", "convert requirements to dashboard spec", "analyze my business requirements", or needs guidance on translating business questions into technical dashboard specifications, selecting appropriate widget types based on data characteristics, discovering relevant datasets for a domain, or generating structured requirements for the create-dashboard workflow.
---

# Dashboard Planner

Translate business requirements into a structured dashboard plan by analyzing available datasets and mapping fields to appropriate visualizations.

## Output Location

All plans are saved to **`plans/`** folder in the workspace:
```
plans/
└── <dashboard-slug>.md    # e.g., plans/support-team.md
```

## When to Use

Use in **plan mode** before `/create-dashboard` when:
- User has vague business requirements ("track support metrics")
- User doesn't know which datasets to use
- Requirements need translation from business language to technical spec

## Workflow

### Step 1: Understand Requirements

Extract:
- **Domain:** What area? (support, customers, product)
- **Questions:** What do they want to answer?
- **Metrics:** Any specific KPIs mentioned?

### Step 2: Discover Datasets

```bash
dashboard-sync dataset list
```

**Note on dataset names**: The CLI now supports both display names (e.g., `devrev.opportunity`) and canonical names (e.g., `devrev.dim_opportunity`). The fetch command will automatically resolve display names to their canonical form.

Filter by domain keywords:
- Support → `dim_ticket`, `fact_ticket_stage_transitions`
- Customers → `dim_account`, `dim_contact`, `dim_opportunity`
- Product → `dim_issue`, `dim_feature`

### Step 3: Fetch and Analyze Schemas

For each selected dataset:
```bash
dashboard-sync dataset fetch <dataset>
```

Read schema files from `datasets/` directory. Identify:
- **timestamp fields** → Time-series candidates
- **enum fields** → Category dimensions (check cardinality via `value_set`)
- **numeric fields** → Measures (COUNT, SUM, AVG)
- **ID fields** → COUNT DISTINCT or grouping

**Note:** For detailed field type mappings and validation rules, see the **widget-development skill** which contains the authoritative technical reference.

### Step 3.5: Assess Data Viability (MANDATORY)

After fetching schemas, sample actual data to validate widget feasibility.

**Why**: Schema describes structure; data reveals reality. Assessment prevents failures from:
- Empty filter results (enum values differ from schema)
- Sparse fields (high NULL rates on grouping dimensions)
- Query timeouts (large fact tables without filters)
- Type mismatches (VARCHAR storing numbers)

**Process**:

1. **Sample each unique dataset**:
   ```bash
   dashboard-sync dataset query <dataset> --limit 20
   ```

2. **For each planned widget, assess**:
   - Field population rates (check NULL %)
   - Actual enum values (case-sensitive match)
   - Time range coverage (MIN/MAX dates)
   - Filter feasibility (test key conditions)

3. **Classify viability**: PASS, WARN, or BLOCK

4. **Document in plan**: Add assessment block per widget + summary table

See `references/data-assessment.md` for detailed checklist and output format.

**Blocking rule**: If any widget is BLOCK status, flag in summary and recommend alternatives.

### Step 4: Map Questions to Widgets

| Business Question Pattern | Widget Type |
|---------------------------|-------------|
| "How many X?" | metric |
| "X over time?" | line |
| "X by category?" | bar |
| "Distribution of X?" | donut |
| "Details of X?" | table |

### Step 5: Write Plan

Write to `plans/<dashboard-slug>.md` with:
- Widget specifications (Type, Dataset, Measure, etc.)
- **Data Assessment block per widget** (from Step 3.5)
- **Assessment Summary table** (from Step 3.5)
- Organization tabs
- Assumptions (including data-driven assumptions)

Use simple Markdown:

```markdown
# Dashboard: Support Team Performance

## Purpose
Track ticket health and team efficiency.

## Widgets

### 1. Open Tickets
- **Type:** metric
- **Dataset:** devrev.dim_ticket
- **Measure:** COUNT(*) WHERE status IN ('open', 'in_progress')
- **Rationale:** Current workload indicator

### 2. Resolution Time Trend
- **Type:** line
- **Dataset:** devrev.fact_ticket_stage_transitions
- **X-axis:** transition_date (weekly)
- **Y-axis:** AVG(time_in_stage_hours) WHERE stage_type = 'resolved'
- **Rationale:** Track efficiency over time

### 3. Tickets by Priority
- **Type:** bar
- **Dataset:** devrev.dim_ticket
- **Dimension:** priority (enum: blocker, high, medium, low)
- **Measure:** COUNT(*)
- **Filter:** status != 'closed'
- **Rationale:** Severity distribution

## Organization

| Tab | Widgets | Purpose |
|-----|---------|---------|
| Overview | 1, 2 | Quick health check |
| Details | 3 | Deep dive |

## Assumptions

1. "Open" includes both 'open' and 'in_progress' status
2. Resolution time = time in 'resolved' stage
3. Weekly aggregation for trends
```

## Widget Type Selection

Choose based on data characteristics:

| Data Shape | Widget | Example |
|------------|--------|---------|
| Single number | metric | "Total tickets: 42" |
| Value + time | line | "Tickets over past 30 days" |
| Value + category (< 10 items) | bar | "Tickets by priority" |
| Value + category (part-of-whole) | donut | "% by status" |
| Multiple columns + rows | table | "Ticket list with owner, date" |

## Common Dataset Patterns

### Support Domain
- `dim_ticket` - Current ticket state, priority, status, owner
- `fact_ticket_stage_transitions` - Ticket lifecycle events, resolution times

### Customer Domain
- `dim_account` - Accounts, tiers, health scores
- `dim_contact` - Contact information

### Product Domain
- `dim_issue` - Engineering issues, severity, status
- `dim_feature` - Feature requests

## Technical Truth Sources

The planner focuses on **conceptual mapping**. For technical implementation:

1. **Field type validation** → See `widget-development` skill and `scripts/widget/lib/rules/field_schema_rules.py`
2. **Type mappings** → See `scripts/widget/lib/rules/type_mapping_rules.py`
3. **SQL patterns** → See `widget-development` references on two-layer architecture
4. **Dashboard CREATE format** → See `dashboard-development` skill

## What Planner Does NOT Cover

The planner produces a **conceptual plan**. Technical details handled by other skills:

| Aspect | Handled By |
|--------|-----------|
| Field schema structure | widget-development |
| SQL expression syntax | widget-development |
| Meerkat type mappings | widget-development |
| Dashboard JSON format | dashboard-development |
| Grid positioning | dashboard-development |

## Tips

- Fetch schemas **before** finalizing widget specs
- Check enum cardinality in schema's `value_set` field
- Use widget-development skill when building actual widgets
- Plan focuses on WHAT to build; creators handle HOW
