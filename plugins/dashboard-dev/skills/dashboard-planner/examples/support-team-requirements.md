# Dashboard: Support Team Performance

## Purpose

Monitor support ticket health and team efficiency. Used by support managers for daily standups and capacity planning.

## Widgets

### 1. Open Tickets
- **Type:** metric
- **Dataset:** devrev.dim_ticket
- **Measure:** COUNT(*) WHERE status IN ('open', 'in_progress')
- **Rationale:** Shows current workload at a glance

#### Data Assessment
- **Viability:** PASS
- **Sample:** 20 rows from devrev.dim_ticket
- **Fields assessed:**
  - `status`: 100% populated, values: ['open', 'in_progress', 'closed', 'waiting']
  - `id`: 100% populated
- **Filter test:** status IN ('open', 'in_progress') returns 156 rows
- **Risks:** None
- **Notes:** Ready for widget generation

### 2. Average Resolution Time
- **Type:** metric
- **Dataset:** devrev.fact_ticket_stage_transitions
- **Measure:** AVG(time_in_stage_hours) WHERE stage_type = 'resolved'
- **Filter:** Last 30 days
- **Rationale:** Key efficiency indicator

#### Data Assessment
- **Viability:** PASS
- **Sample:** 20 rows from devrev.fact_ticket_stage_transitions
- **Fields assessed:**
  - `time_in_stage_hours`: 95% populated, range: 0.5 - 248.3
  - `stage_type`: 100% populated, values: ['open', 'in_progress', 'resolved', 'waiting']
- **Filter test:** stage_type = 'resolved' AND last 30 days returns 89 rows
- **Risks:** None
- **Notes:** Ready for widget generation

### 3. SLA Compliance Rate
- **Type:** metric
- **Dataset:** devrev.dim_ticket
- **Measure:** COUNT(*) WHERE is_sla_breached = false / COUNT(*) (as percentage)
- **Filter:** status = 'closed', last 30 days
- **Rationale:** Customer satisfaction indicator

#### Data Assessment
- **Viability:** PASS
- **Sample:** 20 rows from devrev.dim_ticket
- **Fields assessed:**
  - `is_sla_breached`: 100% populated, values: [true, false]
  - `status`: 100% populated
- **Filter test:** status = 'closed' AND last 30 days returns 72 rows
- **Risks:** None
- **Notes:** Ready for widget generation

### 4. Tickets by Priority
- **Type:** bar
- **Dataset:** devrev.dim_ticket
- **Measure:** COUNT(*)
- **Dimension:** priority (enum: blocker, high, medium, low)
- **Filter:** status != 'closed'
- **Rationale:** Severity distribution of active workload

#### Data Assessment
- **Viability:** PASS
- **Sample:** 20 rows from devrev.dim_ticket
- **Fields assessed:**
  - `priority`: 100% populated, values: ['blocker', 'high', 'medium', 'low']
- **Filter test:** status != 'closed' returns 156 rows
- **Risks:** None
- **Notes:** Enum values confirmed to match schema exactly

### 5. Tickets by Status
- **Type:** donut
- **Dataset:** devrev.dim_ticket
- **Measure:** COUNT(*)
- **Dimension:** status (enum: open, in_progress, waiting, closed)
- **Rationale:** Lifecycle distribution overview

#### Data Assessment
- **Viability:** PASS
- **Sample:** 20 rows from devrev.dim_ticket
- **Fields assessed:**
  - `status`: 100% populated, values: ['open', 'in_progress', 'waiting', 'closed']
- **Filter test:** No filter needed (all statuses included)
- **Risks:** None
- **Notes:** Enum values confirmed to match schema exactly

### 6. Ticket Creation Trend
- **Type:** line
- **Dataset:** devrev.dim_ticket
- **Measure:** COUNT(*)
- **Dimension:** created_date (weekly aggregation)
- **Filter:** Last 90 days
- **Rationale:** Track incoming workload patterns

#### Data Assessment
- **Viability:** PASS
- **Sample:** 20 rows from devrev.dim_ticket
- **Fields assessed:**
  - `created_date`: 100% populated, range: 2024-05-15 to 2025-01-28
- **Filter test:** Last 90 days returns 312 rows
- **Risks:** None
- **Notes:** Date range covers 8+ months, adequate for 90-day analysis

### 7. Resolution Time Trend
- **Type:** line
- **Dataset:** devrev.fact_ticket_stage_transitions
- **Measure:** AVG(time_in_stage_hours)
- **Dimension:** transition_date (weekly aggregation)
- **Filter:** stage_type = 'resolved', last 90 days
- **Rationale:** Track team efficiency over time

#### Data Assessment
- **Viability:** PASS
- **Sample:** 20 rows from devrev.fact_ticket_stage_transitions
- **Fields assessed:**
  - `transition_date`: 100% populated, range: 2024-06-01 to 2025-01-28
  - `time_in_stage_hours`: 95% populated
- **Filter test:** stage_type = 'resolved' AND last 90 days returns 234 rows
- **Risks:** None
- **Notes:** Adequate data coverage for trend analysis

### 8. Tickets by Owner
- **Type:** table
- **Dataset:** devrev.dim_ticket
- **Columns:** owner_name, open_count, in_progress_count, avg_age_days
- **Filter:** status != 'closed'
- **Rationale:** Workload distribution across team members

#### Data Assessment
- **Viability:** WARN
- **Sample:** 20 rows from devrev.dim_ticket
- **Fields assessed:**
  - `owner_id`: 68% populated (32% NULL - unassigned tickets)
  - `owner_name`: 68% populated (follows owner_id)
  - `status`: 100% populated
- **Filter test:** status != 'closed' AND owner_id IS NOT NULL returns 106 rows
- **Risks:** 32% of tickets have no owner assigned
- **Notes:** Widget should handle NULL owners. Options: (1) Add "Unassigned" category via COALESCE, or (2) Filter to assigned tickets only. Recommend option 1 for complete visibility.

## Data Assessment Summary

| Widget | Dataset | Viability | Key Findings |
|--------|---------|-----------|--------------|
| 1. Open Tickets | dim_ticket | PASS | All fields 100% populated |
| 2. Avg Resolution Time | fact_transitions | PASS | time_in_stage_hours 95% populated |
| 3. SLA Compliance | dim_ticket | PASS | is_sla_breached 100% populated |
| 4. By Priority | dim_ticket | PASS | Enum values confirmed |
| 5. By Status | dim_ticket | PASS | Enum values confirmed |
| 6. Creation Trend | dim_ticket | PASS | created_date covers 8+ months |
| 7. Resolution Trend | fact_transitions | PASS | Date range adequate |
| 8. By Owner | dim_ticket | WARN | owner_id 32% NULL |

**Blocked:** 0 widgets
**Warnings:** 1 widget (Widget 8 - owner NULL handling needed)

## Organization

| Tab | Widgets | Purpose |
|-----|---------|---------|
| Overview | 1, 2, 3, 4, 5 | Quick health check and current state |
| Trends | 6, 7 | Historical analysis and patterns |
| Team | 8 | Capacity planning and workload balance |

## Assumptions

1. **Status interpretation:** "Open" includes both 'open' and 'in_progress' status values
2. **Resolution time:** Measured from 'resolved' stage transitions only, not total ticket age
3. **Time windows:** 30 days for metrics (recent performance), 90 days for trends (quarterly view)
4. **Aggregation:** Weekly for trend charts (balances detail vs. noise for 90-day span)
5. **SLA breach:** Using platform's built-in `is_sla_breached` boolean field
6. **Owner assignment:** Assumes single owner per ticket (not team assignments)
7. **NULL handling:** Widget 8 will use COALESCE(owner_name, 'Unassigned') per data assessment
