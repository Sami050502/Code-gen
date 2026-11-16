# Dataset Patterns by Domain

Quick reference for selecting datasets based on business domain.

## Dataset Discovery and Naming

### Display Names vs. Canonical Names

The CLI now supports both naming formats:

| Format Type | Example | Usage |
|-------------|---------|-------|
| Display name | `devrev.opportunity` | Shown in `dataset list` output |
| Canonical name | `devrev.dim_opportunity` | Traditional format with prefix |

**Note**: The `dashboard-sync dataset fetch` command automatically resolves display names to canonical names. You can use either format.

### Dataset Prefixes

DevRev datasets follow naming conventions:
- `dim_` - Dimension tables (current state snapshots)
- `fact_` - Fact tables (historical event streams)
- `insights_` - Pre-aggregated analytics tables

### Discovery Command

```bash
dashboard-sync dataset list                # List all datasets
dashboard-sync dataset list --scope system # Platform datasets only
dashboard-sync dataset list --scope org    # Custom objects only
```

Filter output by domain keywords to find relevant datasets.

## Domain Reference

### Support / Customer Service

**Primary:**
- `devrev.dim_ticket` - Current ticket state
- `devrev.fact_ticket_stage_transitions` - Ticket lifecycle events

**Supporting:**
- `devrev.dim_conversation` - Support conversations
- `devrev.dim_dev_user` - Support agents

**Common Questions:**
| Question | Widget | Dataset |
|----------|--------|---------|
| How many open tickets? | metric | dim_ticket |
| Resolution time trend? | line | fact_ticket_stage_transitions |
| Tickets by priority? | bar | dim_ticket |
| Ticket list by owner? | table | dim_ticket |

---

### Customer Success

**Primary:**
- `devrev.dim_account` - Customer accounts
- `devrev.dim_contact` - Contact information

**Supporting:**
- `devrev.fact_account_health` - Health snapshots (if available)

**Common Questions:**
| Question | Widget | Dataset |
|----------|--------|---------|
| Total active accounts? | metric | dim_account |
| Accounts by tier? | bar/donut | dim_account |
| Account health trend? | line | fact_account_health |

---

### Product / Engineering

**Primary:**
- `devrev.dim_issue` - Engineering issues
- `devrev.dim_feature` - Feature requests

**Supporting:**
- `devrev.fact_issue_transitions` - Issue lifecycle (if available)
- `devrev.dim_part` - Product components

**Common Questions:**
| Question | Widget | Dataset |
|----------|--------|---------|
| Open issues count? | metric | dim_issue |
| Issues by severity? | bar | dim_issue |
| Feature request list? | table | dim_feature |

---

### Knowledge Base

**Primary:**
- `devrev.dim_article` - KB articles
- `devrev.fact_article_views` - View metrics (if available)

**Common Questions:**
| Question | Widget | Dataset |
|----------|--------|---------|
| Total articles? | metric | dim_article |
| Articles by category? | bar | dim_article |
| Top viewed articles? | table | fact_article_views |

---

## Dataset Naming Convention

| Prefix | Purpose | Use For |
|--------|---------|---------|
| `dim_` | Current state snapshot | "How many now?" questions |
| `fact_` | Historical events | "Over time?" questions |

## Key Fields by Dataset

### dim_ticket
- `status` (enum) - open, in_progress, waiting, closed
- `priority` (enum) - blocker, high, medium, low
- `created_date` (timestamp)
- `owner_id` (id)

### dim_account
- `status` (enum) - active, inactive, churned
- `tier` (enum) - enterprise, business, starter
- `health_score_category` (enum) - healthy, at_risk, critical

### dim_issue
- `stage` (enum) - backlog, triage, prioritized, in_development, completed
- `severity` (enum) - blocker, major, minor
- `created_date` (timestamp)

## Schema Verification

Always verify actual fields by fetching the schema:

```bash
dashboard-sync dataset fetch dim_ticket
```

Then read `datasets/devrev.dim_ticket.yaml` for:
- Actual field names
- Field types
- Enum values (in `value_set`)
- Cardinality

## Tips

- Start with `dim_*` tables for current state
- Use `fact_*` tables for time-series trends
- Fetch schemas to verify field existence
- Check enum `cardinality` before using as dimension
- Some datasets may not be available in all orgs
