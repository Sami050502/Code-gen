---
name: Ponos Development
description: This skill should be used when the user asks to "create a Ponos job", "write YAML job", "cross-org dataset", "camel publisher", "test Ponos", "run integration tests", or mentions Ponos job configuration, scheduling, or deployment. Provides comprehensive guidance for developing Ponos jobs.
version: 1.0.0
---

# Ponos Job Development

## Overview

Ponos is a job orchestrator for executing scheduled jobs in BigQuery. Use Ponos for cross-org datasets that aggregate data across all organizations and require production deployment.

**When to use Ponos:**
- Cross-org aggregations (data from multiple dev_oids)
- Production scheduled jobs
- Publishing to stock datasets
- Complex multi-stage pipelines

**When to use PaaS instead:**
- Org-specific datasets (single dev_oid)
- Quick iteration and testing
- Ad-hoc analytics

## Job Types

| Aspect | Summary Jobs | Metrics Jobs | Stock Tables |
|--------|-------------|-------------|--------------|
| Purpose | Aggregate data into Oasis datasets | Publish org metrics to Tapio | Mirror BQ tables to Oasis |
| Query | Real analytical queries | Real queries with metric format | Dummy (`WHERE 1 = 0`) or staging |
| Publisher | `camel` + `gcs_query` | `tapio` | `camel` + `gcs_query` |
| Tags | `"summary"` | `"metrics"` | `"summary"` |
| `use_gcs_destination` | No | Yes (on query) | No |
| `dataset_config` | Yes | No | Yes, `create_oasis_dataset: true` |
| Location | `jobs/configs/summary_jobs/` | `jobs/configs/metrics_jobs/` | `jobs/configs/stock_tables/` |

## Job YAML Structure

### Required Fields

```yaml
name: "job_name_descriptive"
short_name: "JOB_SHORT"  # Unique, <=20 chars
owners: ["email@devrev.ai"]
is_disabled: false
schedule_type: "periodic"  # or "onetime"
schedule_frequency_in_minutes: 60m  # Min 15m
delay_time_in_minutes: 30m  # Wait before processing
tags: "summary"  # "summary" or "metrics"
start_at: 2025-01-01
end_at: 2030-12-31
environments:
  - "local"
  - "dev.dvrv-us-1"
  - "prod.dvrv-us-1"
env_configs:
  "local":
    config_values:
      source_project_name: "app-devrev-dev"
      source_dataset_name: "us_east1_devrev"
      destination_project_name: "app-devrev-dev"
      destination_dataset_name: "us_east1_summary_jobs_test"
      gcs_bucket_name: "devrev-ponos-test-bucket"
job_activities:
  - type: "query"
    queries: [...]
  - type: "publisher"
    publishers: [...]
```

### Key Configuration Fields

| Field | Description | Required |
|-------|-------------|----------|
| `name` | Human-readable job name | Yes |
| `short_name` | Unique identifier for temporal workflows | Yes |
| `owners` | Email addresses for notifications | Yes |
| `tags` | Job category: `"summary"` or `"metrics"` | Yes |
| `schedule_frequency_in_minutes` | Run interval (min 15m) | For periodic |
| `delay_time_in_minutes` | Wait before processing (default 12h) | No |
| `environments` | Where to deploy (local, dev, qa, prod) | Yes |
| `env_configs` | Environment-specific config_values | Yes |

### Environment Naming

Two patterns are used:

**Simple:** `"local"`, `"dev"`, `"qa"`, `"prod"`

**Regional:** `"local"`, `"dev.dvrv-us-1"`, `"qa.dvrv-us-1"`, `"prod.dvrv-us-1"`

Mixed patterns are common (simple for dev, regional for qa/prod). The `env_configs` keys use the base name (e.g., `"dev"` matches both `"dev"` and `"dev.dvrv-us-1"`).

## env_configs and config_values

Every Ponos job must define environment-specific configuration values. These values become template variables accessible in queries and publisher configs.

### Structure

```yaml
env_configs:
  "local":
    config_values:
      source_project_name: "app-devrev-dev"
      source_dataset_name: "us_east1_devrev"
      destination_project_name: "app-devrev-dev"
      destination_dataset_name: "us_east1_summary_jobs_test"
      gcs_bucket_name: "devrev-ponos-test-bucket"
  "dev":
    config_values:
      source_project_name: "app-devrev-dev"
      source_dataset_name: "us_east1_devrev"
      destination_project_name: "app-devrev-dev"
      destination_dataset_name: "us_east1_summary_jobs"
      gcs_bucket_name: "devrev-ponos-dev-bucket"
  "qa":
    config_values:
      source_project_name: "app-devrev-qa"
      source_dataset_name: "us_east1_devrev"
      destination_project_name: "app-devrev-qa"
      destination_dataset_name: "us_east1_summary_jobs"
      gcs_bucket_name: "devrev-ponos-qa-bucket"
  "prod":
    config_values:
      source_project_name: "app-devrev-prod"
      source_dataset_name: "us_east1_devrev"
      destination_project_name: "app-devrev-prod"
      destination_dataset_name: "us_east1_summary_jobs"
      gcs_bucket_name: "devrev-ponos-prod-bucket"
```

### Standard config_values

| Key | Description | Example |
|-----|-------------|---------|
| `source_project_name` | GCP project for source data | `app-devrev-dev` |
| `source_dataset_name` | BigQuery source dataset | `us_east1_devrev` |
| `destination_project_name` | GCP project for output | `app-devrev-dev` |
| `destination_dataset_name` | BigQuery output dataset | `us_east1_summary_jobs` |
| `gcs_bucket_name` | GCS bucket for exports | `devrev-ponos-dev-bucket` |
| `aws_s3_bucket_name` | S3 bucket (metrics jobs) | `serengeti-dev` |
| `fastly_dataset_name` | Fastly dataset (if needed) | `us_east1_fastly` |

**Rule:** At minimum, `"local"` must be defined. Other environments inherit from Ponos framework defaults, but specifying all environments explicitly is safer and clearer.

## Template Variables

Ponos uses Go template syntax `{{.variable_name}}`. Variables come from three sources:

### 1. Framework-Injected (automatic, no config needed)

| Variable | Description | Format |
|----------|-------------|--------|
| `{{.record_date}}` | Current processing date | `DATE("2025-01-15")` |
| `{{.agg_start_date}}` | Aggregation interval start | `TIMESTAMP("2025-01-15T00:00:00Z")` |
| `{{.agg_end_date}}` | Aggregation interval end | `TIMESTAMP("2025-01-16T00:00:00Z")` |
| `{{.agg_interval_year}}` | Year from agg_end_date | Integer |
| `{{.agg_interval_month}}` | Month from agg_end_date | Integer (1-12) |
| `{{.agg_interval_day}}` | Day from agg_end_date | Integer (1-31) |
| `{{.devo_display_id}}` | Dev org display ID | `"DEV-787"` |
| `{{.devo_don}}` | Dev org DON | `"don:core:dvrv-us-1:devo/787"` |
| `{{.dev_oid}}` | Dev org ID number | `"787"` |

### 2. From config_values (defined per environment in env_configs)

| Variable | Description |
|----------|-------------|
| `{{.source_project_name}}` | BQ source project |
| `{{.source_dataset_name}}` | BQ source dataset |
| `{{.destination_project_name}}` | BQ destination project |
| `{{.destination_dataset_name}}` | BQ destination dataset |
| `{{.gcs_bucket_name}}` | GCS bucket name |
| `{{.aws_s3_bucket_name}}` | S3 bucket name (metrics) |

### 3. From query_args (custom per-query, per-environment)

Any key defined in `query_args` becomes a template variable:

```yaml
queries:
  - query_id: "my_query"
    query_args:
      "local":
        custom_dev_org_id: "DEV-787"
        staging_table: "staging_v1"
      "dev":
        custom_dev_org_id: "DEV-787"
        staging_table: "staging_v1"
      "prod":
        custom_dev_org_id: "DEV-113ampvmX3"
        staging_table: "staging_prod"
    query: |
      SELECT "{{.custom_dev_org_id}}" AS dev_oid
      FROM `{{.source_project_name}}.{{.source_dataset_name}}.{{.staging_table}}`
```

**CRITICAL:** Always use three-part FROM clauses: `{{.source_project_name}}.{{.source_dataset_name}}.table_name`

> **Note on two-part FROM in older jobs:** Some existing jobs use two-part references like `` `{{.source_dataset_name}}.table` `` (without `source_project_name`). This works because Ponos fills the project from its global config when `source_project_name` is empty. However, the explicit three-part format is preferred for clarity and should always be used in new jobs.

## CRITICAL: Do Not Export STRUCT Types

**Camel publisher CANNOT handle BigQuery STRUCT types.** If your source table has STRUCT columns, you MUST convert them to JSON strings:

```sql
-- BAD: Camel will fail on STRUCT columns
SELECT stage, properties FROM `{{.source_project_name}}.{{.source_dataset_name}}.fact_ticket`

-- GOOD: Convert STRUCTs to JSON strings
SELECT
  TO_JSON_STRING(stage) AS stage_json,
  TO_JSON_STRING(properties) AS properties_json
FROM `{{.source_project_name}}.{{.source_dataset_name}}.fact_ticket`

-- GOOD: Exclude STRUCTs with EXCEPT and add JSON versions
SELECT * EXCEPT(stage, properties),
  TO_JSON_STRING(stage) AS stage_json,
  TO_JSON_STRING(properties) AS properties_json
FROM `{{.source_project_name}}.{{.source_dataset_name}}.fact_ticket`
```

**Rule:** If a column is a STRUCT or ARRAY<STRUCT>, always use `TO_JSON_STRING()` to convert it to a VARCHAR/STRING before exporting via camel.

## Query Activity

### Standard Pattern: Dummy Query + Publisher select_query

The most common pattern (used by the vast majority of production jobs). The `query:` field contains a dummy query (`SELECT true`), and the real analytical SQL goes in the publisher's `select_query`:

```yaml
job_activities:
  - type: "query"
    queries:
      - query_id: "my_summary"
        short_name: "MS"
        description: "Daily summary aggregation"
        query: SELECT true
        query_args:
          "local":
            devo_display_id: "DEV-787"
          "dev":
            devo_display_id: "DEV-787"
          "prod":
            devo_display_id: "DEV-XXXXX"
```

The publisher's `select_query` then contains the actual analytical SQL (see Publisher section below).

**Why dummy queries?** The publisher's `select_query` queries directly from source tables and exports to Oasis without needing an intermediate BQ destination table. This is simpler and avoids extra BQ storage costs.

### Alternative Pattern: Real Query + Destination Table

Only needed for special cases like multi-step DELETE + INSERT jobs:

```yaml
queries:
  - query_id: "my_insert"
    short_name: "MI"
    destination_table_name: "my_table"
    table_creation_config:
      description: "Summary table"
      partition_key: "record_date"
      time_partition_type: "day"
      cluster_keys:
        - "dev_oid"
    query: |
      SELECT dev_oid, DATE({{.agg_start_date}}) AS record_date, COUNT(*) AS total
      FROM `{{.source_project_name}}.{{.source_dataset_name}}.fact_ticket`
      WHERE DATE(modified_date) = DATE({{.agg_start_date}})
      GROUP BY 1, 2
```

### table_creation_config (only for real query pattern)

| Field | Description | Required |
|-------|-------------|----------|
| `description` | Human-readable table description | Yes |
| `partition_key` | Column name for BQ partitioning | Yes (for partitioned) |
| `time_partition_type` | `"day"` or `"hour"` (default: `"day"`) | No |
| `cluster_keys` | Up to 4 clustering columns | No |

**Note:** `table_creation_config` and `destination_table_name` are only needed when the query writes to a BQ intermediate table. The standard dummy query pattern does not need them.

### query_args (REQUIRED)

**Every Ponos job MUST include `query_args`** with per-environment org identifiers. This is required because `owner_display_id` and dev_oid filters need environment-specific values to work in dev, qa, and prod:

```yaml
queries:
  - query_id: "my_query"
    query_args:
      "local":
        custom_dev_org_id: "DEV-787"
      "dev":
        custom_dev_org_id: "DEV-787"
      "qa":
        custom_dev_org_id: "DEV-2Ijnu24fff"
      "prod":
        custom_dev_org_id: "DEV-113ampvmX3"
    query: |
      SELECT "{{.custom_dev_org_id}}" AS dev_oid ...
```

`query_args` variables are accessible in both the query and in publisher `select_query`.

## Publisher Types

### Camel Publisher (for Oasis datasets)

Publishes query results to Oasis datasets. When using the standard dummy query pattern, the `select_query` contains the actual analytical SQL:

```yaml
- type: "camel"
  query_id: "my_summary"
  camel_publisher_activity:
    dataset_config:
      name: "my_dataset"
      title: "My Dataset"
      description: "Dataset description"
      create_oasis_dataset: true
      timestamp_column_name: "record_date"
      owner_display_id: "{{.devo_display_id}}"
    exporter_type: "gcs_query"
    exporter_gcs_query:
      destination_file_format: "PARQUET"
      select_query: |
        SELECT
          dev_oid,
          DATE({{.agg_start_date}}) AS record_date,
          COUNT(DISTINCT id) AS ticket_count
        FROM `{{.source_project_name}}.{{.source_dataset_name}}.fact_ticket`
        WHERE dev_oid = '{{.devo_display_id}}'
          AND DATE(modified_date) = DATE({{.agg_start_date}})
        GROUP BY 1, 2
```

### dataset_config Fields

| Field | Description | Usage |
|-------|-------------|-------|
| `name` | Dataset name in Oasis | Required |
| `title` | Human-readable title | Standard (92%) |
| `description` | Dataset description | Standard (97%) |
| `create_oasis_dataset` | Auto-create if not exists | Standard (88%) |
| `owner_display_id` | Dataset owner | Standard (92%), use `"{{.devo_display_id}}"` |
| `timestamp_column_name` | Time column for partitioning | Common (69%) |
| `access_level` | `"EXTERNAL"` or `"INTERNAL"` | Occasional (28%) |
| `is_system` | System dataset flag | Occasional (39%) |

### Tapio Publisher (for metrics)

Publishes metrics to Tapio (used with `tags: "metrics"`):

```yaml
- type: "tapio"
  query_id: "metrics_query"
  tapio_publisher_activity:
    child_batch_size: 50000
```

Metrics queries must output this schema:
```sql
SELECT
  "{{.devo_don}}" AS dev_oid,
  org_ref,
  "" AS user_ref,
  "metric_name" AS metric_name,
  {{.agg_end_date}} AS metric_timestamp,
  CAST(value AS float64) AS metric_value,
  ARRAY<STRUCT<name string, value string>>[] AS metric_dimensions
```

Also requires `use_gcs_destination: true` on the query activity.

### Storage Publisher (for exports)

Exports to GCS or S3:

```yaml
- type: "storage"
  query_id: "export_query"
  storage_publisher_activity:
    exporter_type: "gcs_query"
    exporter_gcs_query:
      destination_bucket_name: "{{.gcs_bucket_name}}"
      destination_file_format: "PARQUET"
      select_query: |
        SELECT * FROM `{{.destination_project_name}}.{{.destination_dataset_name}}.table`
```

## Multi-Step Jobs

For jobs that need to DELETE previous data before inserting fresh data (common for re-computing a full time window):

```yaml
job_activities:
  # Step 1: Delete previous data for the date
  - type: "query"
    queries:
      - query_id: "my_job_delete"
        short_name: "D_MJ"
        query: |
          DELETE FROM `{{.destination_project_name}}.{{.destination_dataset_name}}.my_table`
          WHERE DATE(record_date) = DATE({{.agg_start_date}})

  # Step 2: Insert fresh data
  - type: "query"
    queries:
      - query_id: "my_job_insert"
        short_name: "MJ"
        destination_table_name: "my_table"
        table_creation_config:
          description: "My summary table"
          partition_key: "record_date"
          time_partition_type: "day"
          cluster_keys:
            - "dev_oid"
        query: |
          SELECT
            DATE({{.agg_start_date}}) AS record_date,
            dev_oid,
            COUNT(*) AS total
          FROM `{{.source_project_name}}.{{.source_dataset_name}}.fact_ticket`
          WHERE DATE(modified_date) = DATE({{.agg_start_date}})
          GROUP BY 1, 2

  # Step 3: Publish to Oasis
  - type: "publisher"
    publishers:
      - type: "camel"
        query_id: "my_job_insert"
        camel_publisher_activity:
          dataset_config:
            name: "my_dataset"
            title: "My Dataset"
            create_oasis_dataset: true
            timestamp_column_name: "record_date"
            owner_display_id: "{{.devo_display_id}}"
          exporter_type: "gcs_query"
          exporter_gcs_query:
            destination_file_format: "PARQUET"
            select_query: |
              SELECT
                record_date,
                dev_oid,
                total
              FROM `{{.destination_project_name}}.{{.destination_dataset_name}}.my_table`
              WHERE DATE(record_date) = DATE({{.agg_start_date}})
```

Multiple publishers can target different datasets from the same query by referencing the same `query_id`.

## Common Production Patterns

### Dummy Queries (Standard Pattern)

**This is the standard pattern for most Ponos summary jobs.** The `query:` field contains `SELECT true`, and all real SQL goes in the publisher's `select_query`. This avoids creating intermediate BQ destination tables:

```yaml
queries:
  - query_id: "my_query"
    short_name: "MQ"
    description: "My summary query"
    query: SELECT true
    query_args:
      "local":
        devo_display_id: "DEV-787"
      "dev":
        devo_display_id: "DEV-787"
      "prod":
        devo_display_id: "DEV-XXXXX"
```

The publisher's `select_query` then contains the actual analytical SQL that reads from source tables and transforms the data. See the Query Activity section above for details.

### Multiple Publishers per Query

A single query can feed multiple publishers to create different datasets from the same query output:

```yaml
- type: "publisher"
  publishers:
    - type: "camel"
      query_id: "my_query"
      camel_publisher_activity:
        dataset_config:
          name: "full_dataset"
          # ... full dataset config
    - type: "camel"
      query_id: "my_query"
      camel_publisher_activity:
        dataset_config:
          name: "slim_dataset"
          # ... slim version with fewer columns

```

### env_configs: Only "local" Needed

In most jobs, only the `"local"` environment needs explicit `config_values`. Non-local environments (`dev`, `qa`, `prod`) inherit values from the Ponos framework defaults:

```yaml
env_configs:
  "local":
    config_values:
      source_project_name: "app-devrev-dev"
      source_dataset_name: "us_east1_devrev"
      destination_project_name: "app-devrev-dev"
      destination_dataset_name: "us_east1_summary_jobs_test"
      gcs_bucket_name: "devrev-ponos-test-bucket"
# dev, qa, prod - no explicit config needed (framework defaults)
```

Explicit non-local env_configs are only needed when you need custom `config_values` beyond the defaults (e.g., `fastly_dataset_name`, custom `aws_s3_bucket_name`).

## Backfill Partition Limit

**When running backfills, there is a limit of ~100 effective partitions** per backfill execution (AWS Athena limit). If your backfill would create more partitions, split it into multiple runs.

For example, with `time_partition_type: "day"`:
- 90-day backfill = 90 partitions (OK)
- 365-day backfill = 365 partitions (TOO MANY - split into chunks)

**Recommendation:** For large backfills, run multiple smaller backfills covering ~90-day windows.

## Testing Workflow

### Prerequisites

Before testing, ensure:

1. **AWS CLI & SSO** - Configure AWS SSO profile (`aws configure sso`)
2. **kubectl** - Configure EKS cluster access
3. **Shared repo** - Clone devrev/shared for role assumption scripts
4. **macOS only** - Python virtual env may be needed: `python3 -m venv myenv && source myenv/bin/activate && pip install boto3`

### Testing Flow

```
1. Dry Run (--bqdryrun)       →  Validate SQL syntax, no data processed
         ↓
2. Full Integration Test      →  Run without port-forwarding first
         ↓  (if fails for camel publisher)
3. Full Test + Port-Forward   →  Port-forward services and retry
         ↓
Done.
```

### Step 1: Environment Setup

```bash
# Login to AWS SSO
aws sso login --profile dev

# Navigate to shared repo
cd /path/to/shared

# Assume service role
python3 py/utils/aws_role_assumption/assume_service_role.py -s ponos --aws-profile dev

# Source environment
source /tmp/.env
```

If role assumption fails due to ACL limit:
```bash
python3 py/utils/aws_role_assumption/remove_role_trust.py -s ponos --aws-profile dev
# Then retry assume_service_role.py
```

### Step 2: Dry Run Test

Validate SQL syntax without processing data:

```bash
cd /path/to/ponos
source /tmp/.env && make int-test ARGS='--jobpaths=my_job.yaml --bqdryrun'
```

### Step 3: Full Integration Test

Run without port-forwarding first:

```bash
source /tmp/.env && make int-test ARGS='--jobpaths=my_job.yaml'
```

If this passes, the job is fully validated.

### Step 4: Full Test with Port-Forwarding

If step 3 fails because of camel publisher (connection refused / service unavailable):

```bash
# Port-forward services
kubectl -n oasis port-forward service/oasis 7374:80 &
kubectl -n schemaregistry port-forward service/schemaregistry 8889:80 &
kubectl -n pycamel port-forward service/pycamel 8887:80 &
sleep 3

# Run with service endpoints
source /tmp/.env && make int-test ARGS='--jobpaths=my_job.yaml --pycamelendpoint=localhost:8887 --registryendpoint=localhost:8889 --oasisendpoint=localhost:7374 --runcamelasactivity=true'
```

### Step 5: Validate Before Commit

Run the static validation script:

```bash
python ${CLAUDE_PLUGIN_ROOT}/scripts/validate_job.py my_job.yaml
```

## Job File Location

Place job YAML files in the ponos repository:
- `jobs/configs/summary_jobs/` - Summary and aggregation jobs
- `jobs/configs/metrics_jobs/` - Metrics jobs
- `jobs/configs/stock_tables/` - Stock table publishing jobs

## Deployment & Promotion Workflow

After successful testing, jobs follow this promotion path:

### Step 1: Deploy to Dev

1. Create PR to ponos repo with your job YAML
2. Add job path to `configs/dev/config.yaml`:
   ```yaml
   jobs:
     - jobs/configs/summary_jobs/my_job.yaml
   ```
3. Merge PR and verify in Temporal dashboard

### Step 2: Monitor in Dev (2+ days recommended)

- Check Temporal for successful executions
- Verify data in BigQuery destination tables
- Check Oasis dataset for correct data

### Step 3: Promote to QA/Prod

1. Add job path to `configs/qa/config.yaml` and/or `configs/prod/config.yaml`
2. Create PR for promotion
3. Monitor after merge

**Important:** Each environment config file (`configs/<env>/config.yaml`) lists which jobs run in that environment. A job YAML can exist in the repo but won't execute in an environment until it's added to that environment's config file.

## Additional Resources

### Reference Files

- **`references/yaml-examples.md`** - Complete job YAML examples

### Scripts

- **`${CLAUDE_PLUGIN_ROOT}/scripts/setup_ponos_env.sh`** - Environment setup
- **`${CLAUDE_PLUGIN_ROOT}/scripts/port_forward.sh`** - Port forwarding utility
- **`${CLAUDE_PLUGIN_ROOT}/scripts/validate_job.py`** - Job validation
