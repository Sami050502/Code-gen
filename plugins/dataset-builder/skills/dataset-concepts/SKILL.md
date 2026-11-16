---
name: Dataset Concepts
description: This skill should be used when the user asks about "Oasis dataset", "dim vs fact", "partitioning", "clustering", "dataset schema", "timestamp granularity", "data window", or mentions dataset design concepts. Provides foundational knowledge about DevRev's Oasis analytics platform and dataset architecture.
version: 1.0.0
---

# Dataset Concepts for DevRev Oasis Platform

## Overview

The Oasis platform stores and serves analytics datasets in DevRev. Understanding its concepts is essential for creating custom datasets that perform well and integrate correctly with DevRev's analytics infrastructure.

## Why Create Custom Datasets?

**Dimension tables (`dim_*`)** are already directly available in Oasis. You can query them without creating custom datasets.

**Custom datasets are needed when:**
- Aggregating historical data from `fact_*` tables
- Creating time-series metrics and trends
- Pre-computing expensive aggregations for dashboards

## CRITICAL: Source Table Selection

**ALWAYS use `fact_*` tables as your primary data source!**

| Need | Use | Why |
|------|-----|-----|
| Historical data | `fact_*` | Contains time-partitioned events |
| Stage history | `fact_issue`, `fact_ticket` | Tracks transitions over time |
| Current state | Don't create! | `dim_*` already in Oasis |
| Names/attributes | JOIN with `dim_*` | Enrichment only |

**NEVER use `dim_*` as primary source because:**
1. `dim_*` only shows CURRENT state, not history
2. `dim_*` is already directly usable in Oasis
3. Creating from `dim_*` is wasteful and wrong

## Stock Datasets

### Dimension Tables (dim_*) - Directly Usable

Current state data, non-time partitioned. **No need to create custom datasets from these** - they're already in Oasis.

| Table | Description |
|-------|-------------|
| `dim_ticket` | Support tickets (current state) |
| `dim_account` | Customer accounts |
| `dim_revu` | Customer contacts (rev users) |
| `dim_devu` | Internal users (dev users) |
| `dim_issue` | Engineering issues |
| `dim_conversation` | Customer conversations |
| `dim_group` | Teams and groups |
| `dim_product` | Products/parts |

**Use dim_* for:** Direct queries, JOIN enrichment (get names, attributes)

### Fact Tables (fact_*) - Primary Source for Custom Datasets

Historical/time-partitioned data. **This is what you aggregate** when creating custom datasets.

| Table | Description |
|-------|-------------|
| `fact_ticket` | Ticket events over time |
| `fact_events` | General events |
| `fact_timeline` | Timeline events |
| `fact_issue` | Issue events over time |
| `fact_conversation` | Conversation metrics |

**Use fact_* for:** Time-series analysis, trend tracking, historical aggregations

## Custom Datasets (Your Output)

When creating NEW datasets via Ponos or PaaS:

**Primary source:** Always a `fact_*` table (time-partitioned data)
**JOIN sources:** `dim_*` tables for enrichment only (get names, attributes)

**Naming convention:**
- Use descriptive names WITHOUT `dim_` or `fact_` prefixes
- Examples: `ticket_daily_metrics`, `support_trends`, `account_activity`
- Do NOT use: `dim_*` or `fact_*` prefixes (reserved for stock datasets)

## Partitioning

### CRITICAL: Partitioning Affects Data Behavior

| Dataset Type | On Job Run | Use For |
|--------------|------------|---------|
| **Non-partitioned** | All data REPLACED | Current state snapshots |
| **Time-partitioned** | Data APPENDED per partition | Historical data, events |

**Without time partitioning, each job run DELETES all existing data and replaces it!**

For historical/event data (stage history, metrics over time, activity logs), you MUST use time partitioning to preserve data across runs.

### Default Partitioning (dev_oid)

Every dataset automatically partitions by `dev_oid` (organization ID).

**Requirements:**
- Dataset must have a `dev_oid` column
- Maximum 5000 partitions per dataset across all combinations

### Time-Based Partitioning (REQUIRED for historical data)

For historical data from fact tables, partition on a timestamp column.

**Granularity options:**
- `year` - Yearly partitions
- `month` - Monthly partitions (most common)
- `day` - Daily partitions

**Configuration:**
```yaml
partition_columns:
  - name: "record_date"
    type: "TIMESTAMP"
    devrev_field_type: "timestamp"
    timestamp_granularity: "month"
    data_window_granularity: 3
```

**When to use time partitioning:**
- Stage history / transition tracking
- Event logs / activity tracking
- Metrics that accumulate over time
- Any data from `fact_*` tables

### String-Based Partitioning

Partition by categorical values (up to 3 dimensions).

**Example:**
```json
{ "env": "dev", "region": "us-east-1" }
```

**Constraints:** Total unique combinations must stay within 5000 partition limit.

## Data Window

For time-partitioned datasets, the data window indicates data recency within a partition.

### Data Window Granularity

Controls the increments of data windows:
- `minutes` - 10-minute windows (lowest)
- `hour` - 1-hour windows
- `day` - 1-day windows
- `month` - 1-month windows
- `year` - 1-year windows (highest)

**Rule:** Data window granularity must be <= partition granularity.

### Example

For a monthly partitioned dataset with daily data window:
```
Partition: January 2025
Possible data windows:
  - 2025-01-01 to 2025-01-02
  - 2025-01-02 to 2025-01-03
  - ... (31 possible windows)
```

## Clustering

Clustering sorts data within partitions for faster queries.

**Default:** Implicit clustering on `dev_oid` for system datasets.

**Custom clustering:** Up to 2 additional columns.

**Storage order:** `dev_oid, col1, col2`

**Best practices:**
- Choose columns frequently used in WHERE, JOIN, or GROUP BY
- Most selective column first
- Ideal cardinality: 1K-100K unique values
- Very low (boolean) or very high (UUID) reduces effectiveness

## Schema Constraints

### Field Names

- Pattern: `^[a-z0-9_]*$` (lowercase, numbers, underscores only)
- Maximum length: 500 characters

### Timestamps

- Stored in UTC without timezone
- `isAdjustedToUTC=false` in parquet files
- Client must convert to UTC before ingestion

### Data Types

Common types in Oasis schemas:
- `VARCHAR` - Strings
- `BIGINT` - Large integers
- `TIMESTAMP` - Date/time values
- `BOOLEAN` - True/false
- `DOUBLE` - Floating point numbers

## Required Columns

Every dataset must include:

| Column | Purpose |
|--------|---------|
| `dev_oid` | Organization identifier (required for partitioning) |
| `dw_owner_oid` | Data warehouse owner (who owns this data) |

For fact tables, also include a timestamp column for time partitioning.

## Creating a Dataset Schema

### Step 1: Choose Dataset Name

Use a descriptive name that reflects the dataset's purpose:
- `ticket_metrics`, `account_summary`, `support_analytics`
- Do NOT use `dim_` or `fact_` prefixes (reserved for stock datasets)

### Step 2: Identify Partitioning Strategy

- Non-time partitioned (like dim tables): Current state only
- Time-partitioned (like fact tables): Historical/time-series data

### Step 3: Define Columns

List all columns with their types. Follow naming conventions:
- Lowercase with underscores
- Descriptive names
- Include `dev_oid` and `dw_owner_oid`

### Step 4: Configure Partitioning

For non-time partitioned datasets:
- Default dev_oid partitioning only

For time-partitioned datasets:
- Select timestamp column
- Choose appropriate granularity (month is common)
- Set data window granularity

### Step 5: Configure Clustering

Select 0-2 columns that:
- Appear in common queries
- Have moderate cardinality
- Benefit query performance

## API for Dataset Operations

**Create dataset:**
```
POST /internal/oasis.dataset.create
```

**Get dataset:**
```
GET /internal/oasis.dataset.get?name={name}
```

**List datasets:**
```
GET /internal/oasis.dataset.list
```

See `references/oasis-api.md` for complete API documentation.

## Additional Resources

### Reference Files

- **`references/oasis-api.md`** - Oasis API endpoints and examples

### Scripts

- **`${CLAUDE_PLUGIN_ROOT}/scripts/devrev_api.py`** - Make Oasis API calls
