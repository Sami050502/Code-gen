---
name: Ponos Best Practices
description: This skill should be used when the user asks about "Ponos review", "BQ optimization", "query validation", "partition filter", "job validation", "code review criteria", or mentions ensuring job quality before commit. Provides comprehensive review criteria for Ponos jobs.
version: 1.0.0
---

# Ponos Job Best Practices and Review Criteria

## Overview

Before committing Ponos jobs, validate them against the data team's review criteria. This ensures cost efficiency, performance, and correctness.

## Critical BigQuery Optimization

### Partition Filtering (HIGHEST PRIORITY)

Every query on partitioned tables MUST filter on partition columns.

**Required patterns:**
```sql
-- Filter on partition column
WHERE DATE(created_at) = {{.record_date}}
WHERE created_date BETWEEN '2025-01-01' AND '2025-01-31'
WHERE record_date = {{.record_date}}
```

**Avoid:**
```sql
-- NO partition filter - scans entire table!
SELECT * FROM fact_events

-- Function on partition column prevents pruning
WHERE DATE_TRUNC(created_date, MONTH) = '2025-01'
```

### Bounded Date Ranges

Always bound date ranges:

**Good:**
```sql
WHERE created_date >= {{.record_date}} - 7
  AND created_date < {{.record_date}}
```

**Bad:**
```sql
-- Unbounded - scans all historical data!
WHERE created_date >= '2020-01-01'
```

### Avoid SELECT *

Explicitly list needed columns:

**Good:**
```sql
SELECT id, name, created_date, dev_oid
FROM dim_ticket
```

**Bad:**
```sql
-- Reads ALL columns, increases cost
SELECT * FROM dim_ticket
```

## Template Variables

### Required Templates

Always use templates instead of hardcoded values. Variables come from three sources:

**Framework-Injected (automatic):**

| Template | Use For |
|----------|---------|
| `{{.record_date}}` | Current processing date |
| `{{.agg_start_date}}` | Aggregation window start |
| `{{.agg_end_date}}` | Aggregation window end |
| `{{.dev_oid}}` | Organization ID |
| `{{.devo_display_id}}` | DEV-xxx display ID |
| `{{.devo_don}}` | Dev org DON |

**From config_values (defined in env_configs):**

| Template | Use For |
|----------|---------|
| `{{.source_project_name}}` | BQ source project |
| `{{.source_dataset_name}}` | BQ source dataset |
| `{{.destination_project_name}}` | BQ destination project |
| `{{.destination_dataset_name}}` | BQ destination dataset |
| `{{.gcs_bucket_name}}` | GCS bucket |

**From query_args (custom per-query, per-environment):**
- Any key in `query_args` becomes `{{.key_name}}`
- Example: `{{.custom_dev_org_id}}`, `{{.staging_table}}`

**Good:**
```sql
SELECT dev_oid, COUNT(*) AS count
FROM `{{.source_project_name}}.{{.source_dataset_name}}.fact_ticket`
WHERE DATE(created_date) = DATE({{.agg_start_date}})
```

**Bad:**
```sql
-- Hardcoded project and dataset, missing source_project_name
SELECT * FROM `app-devrev-prod.us_east1_devrev.dim_ticket`
WHERE DATE(created_date) = '2025-01-01'
```

## STRUCT Type Warning

**Camel publisher CANNOT export STRUCT or ARRAY<STRUCT> columns.** Convert them first:

```sql
-- Convert STRUCT to JSON string
SELECT TO_JSON_STRING(stage) AS stage_json
-- Or exclude and re-add
SELECT * EXCEPT(stage), TO_JSON_STRING(stage) AS stage_json
```

**Validation check:** If query outputs contain STRUCT columns, the camel export will fail at runtime.

## JOIN Best Practices

### JOIN Order

Place largest table first:
```sql
SELECT ...
FROM fact_events f  -- Largest table first
JOIN dim_ticket t ON f.ticket_id = t.id
JOIN dim_account a ON t.account_id = a.id
```

### Explicit ON Conditions

Always include explicit ON conditions:

**Good:**
```sql
SELECT * FROM a JOIN b ON a.id = b.a_id
```

**Bad:**
```sql
-- Cartesian product!
SELECT * FROM a, b WHERE a.id = b.a_id

-- Missing ON clause
SELECT * FROM a JOIN b
```

### FULL OUTER JOIN

Always use COALESCE for FULL OUTER JOIN:

```sql
SELECT
  COALESCE(a.id, b.id) AS id,
  COALESCE(a.date, b.date) AS date,
  a.metric_a,
  b.metric_b
FROM table_a a
FULL OUTER JOIN table_b b ON a.id = b.id
```

## Aggregation Rules

### GROUP BY Completeness

All non-aggregated columns must be in GROUP BY:

**Good:**
```sql
SELECT dev_oid, status, COUNT(*) AS count
FROM dim_ticket
GROUP BY dev_oid, status
```

**Bad:**
```sql
-- status not in GROUP BY!
SELECT dev_oid, status, COUNT(*) AS count
FROM dim_ticket
GROUP BY dev_oid
```

### WHERE vs HAVING

Filter before aggregation when possible:

**Good:**
```sql
SELECT dev_oid, COUNT(*) AS count
FROM dim_ticket
WHERE status = 'open'  -- Filter first
GROUP BY dev_oid
```

**Less efficient:**
```sql
SELECT dev_oid, status, COUNT(*) AS count
FROM dim_ticket
GROUP BY dev_oid, status
HAVING status = 'open'  -- Filter after aggregation
```

## Performance Optimization

### APPROX Functions

Use approximate functions for large datasets:

```sql
-- Faster, 98%+ accurate
SELECT APPROX_COUNT_DISTINCT(user_id) AS unique_users

-- Exact but slower
SELECT COUNT(DISTINCT user_id) AS unique_users
```

### UNION ALL vs UNION

Prefer UNION ALL when duplicates acceptable:

```sql
-- Faster (no deduplication)
SELECT * FROM table_a
UNION ALL
SELECT * FROM table_b

-- Slower (requires deduplication)
SELECT * FROM table_a
UNION
SELECT * FROM table_b
```

### Safe Division

Use SAFE_DIVIDE to prevent division by zero:

```sql
SELECT SAFE_DIVIDE(total, count) AS average
```

## Job Configuration Validation

### Required Metadata

| Field | Requirement |
|-------|-------------|
| `name` | Present and descriptive |
| `short_name` | Unique, <=20 chars |
| `owners` | Valid email addresses |
| `tags` | `"summary"` or `"metrics"` |
| `schedule_frequency_in_minutes` | >= 15 |

### env_configs Validation

- `env_configs` must have at least `"local"` entry with `config_values`
- Required config_values: `source_project_name`, `source_dataset_name`, `destination_project_name`, `destination_dataset_name`, `gcs_bucket_name`
- For metrics jobs, also require `aws_s3_bucket_name`
- Environment names in `env_configs` must match `environments` list (base names)

### query_args Validation

- All `query_args` environment keys should have matching environments
- All template variables in query text must be resolvable (framework-injected, config_values, or query_args)
- query_args values should differ between environments where appropriate (e.g., `custom_dev_org_id` should differ between dev and prod)

### table_creation_config Validation

- `description` should be present and non-empty
- `partition_key` should match a column in the SELECT output
- `time_partition_type` should be `"day"` or `"hour"` (default `"day"`)
- `cluster_keys` should be columns used in WHERE/GROUP BY/JOIN

### Environment Configuration

Mixed patterns are acceptable (simple for dev, regional for prod):
- Valid: `["local", "dev", "qa", "prod"]`
- Valid: `["local", "dev.dvrv-us-1", "prod.dvrv-us-1"]`
- Valid: `["local", "dev", "qa.dvrv-us-1", "prod.dvrv-us-1"]`

### Query ID Uniqueness

Each `query_id` must be unique within the job.

### FROM Clause Format

Always use three-part references:
- **Good:** `` `{{.source_project_name}}.{{.source_dataset_name}}.fact_ticket` ``
- **Bad:** `` `{{.source_dataset_name}}.fact_ticket` `` (missing project)

## Backfill Limits

**Backfills are limited to ~100 effective partitions** per execution (AWS Athena constraint). For large date ranges, split into multiple ~90-day chunks.

## Security Checklist

- No hardcoded credentials or API keys
- No PII logging or exposure
- Proper dev_oid/customer_oid filtering
- No sensitive data in error messages

## Validation Checklist

Before committing, verify:

**Query:**
1. [ ] Partition filter on ALL partitioned tables
2. [ ] Date ranges bounded and reasonable
3. [ ] No SELECT * (columns explicitly listed)
4. [ ] All JOINs have proper ON conditions
5. [ ] Template variables used (no hardcoded values)
6. [ ] FROM clauses use three-part reference (`project.dataset.table`)
7. [ ] Clustering keys used in WHERE/JOIN/GROUP BY
8. [ ] No correlated subqueries or cartesian products
9. [ ] APPROX functions for large aggregations
10. [ ] NULL handling explicit for OUTER JOINs

**Configuration:**
11. [ ] `env_configs` has `"local"` with all required config_values
12. [ ] `query_args` environments match job environments (if used)
13. [ ] All template variables in queries and publisher `select_query` are resolvable
14. [ ] `table_creation_config` has `description` (only needed for DELETE+INSERT pattern)
15. [ ] `tags` field set to `"summary"` or `"metrics"`
16. [ ] `owner_display_id` set in dataset_config
17. [ ] `time_partition_type` specified if not default "day" (only for real query pattern)
18. [ ] Publisher `select_query` contains actual analytical SQL (for dummy query pattern)

## Pre-Commit Testing Workflow

### 1. Static Validation (no BQ access needed)

```bash
python ${CLAUDE_PLUGIN_ROOT}/scripts/validate_job.py my_job.yaml
```

### 2. Dry Run (validates SQL syntax, no data processed)

```bash
cd /path/to/ponos
source /tmp/.env && make int-test ARGS='--jobpaths=my_job.yaml --bqdryrun'
```

### 3. Full Integration Test (try without port-forwarding first)

```bash
source /tmp/.env && make int-test ARGS='--jobpaths=my_job.yaml'
```

### 4. Full Test with Port-Forwarding (if step 3 fails for camel publisher)

```bash
kubectl -n oasis port-forward service/oasis 7374:80 &
kubectl -n schemaregistry port-forward service/schemaregistry 8889:80 &
kubectl -n pycamel port-forward service/pycamel 8887:80 &
sleep 3

source /tmp/.env && make int-test ARGS='--jobpaths=my_job.yaml --pycamelendpoint=localhost:8887 --registryendpoint=localhost:8889 --oasisendpoint=localhost:7374 --runcamelasactivity=true'
```

### Validation Script Output

**Output:**
```
=== Ponos Job Validation Report ===

ERRORS (1):
  [bigquery] No partition filter detected
    Location: job_activities[0].queries[0]
    Suggestion: Add WHERE clause with partition column

WARNINGS (2):
  [bigquery] SELECT * detected
    Suggestion: Replace with explicit column list
  [bigquery] Hardcoded dataset name
    Suggestion: Use {{.source_dataset_name}}

SUMMARY:
  Errors: 1
  Warnings: 2
```

## Additional Resources

### Reference Files

- **`references/review-criteria-full.md`** - Complete review checklist

### Scripts

- **`${CLAUDE_PLUGIN_ROOT}/scripts/validate_job.py`** - Automated validation
