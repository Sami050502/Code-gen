# Complete Ponos Review Criteria

## BigQuery Optimization Checklist

### Partition Filtering (CRITICAL)

Every query MUST filter on partition columns:

```sql
-- REQUIRED patterns
WHERE DATE(created_at) = {{.record_date}}
WHERE created_date BETWEEN '2025-01-01' AND '2025-01-31'
WHERE record_date = {{.record_date}}

-- NEVER do this (full table scan)
SELECT * FROM fact_events
```

### Column Selection

```sql
-- GOOD: explicit columns
SELECT id, name, created_date, dev_oid FROM dim_ticket

-- BAD: select all
SELECT * FROM dim_ticket
```

### Template Variables

**Framework-Injected (automatic):**

| Variable | Use For |
|----------|---------|
| `{{.record_date}}` | Date filtering |
| `{{.agg_start_date}}` | Aggregation window start |
| `{{.agg_end_date}}` | Aggregation window end |
| `{{.dev_oid}}` | Organization ID |
| `{{.devo_display_id}}` | Display ID (DEV-xxx) |
| `{{.devo_don}}` | Dev org DON |

**From config_values (env_configs):**

| Variable | Use For |
|----------|---------|
| `{{.source_project_name}}` | BQ source project in FROM |
| `{{.source_dataset_name}}` | BQ source dataset in FROM |
| `{{.destination_project_name}}` | BQ destination project |
| `{{.destination_dataset_name}}` | BQ destination dataset |
| `{{.gcs_bucket_name}}` | GCS export bucket |

**From query_args (custom per-query, per-env):**
- Any key in `query_args` becomes `{{.key_name}}`

**FROM clause format:** Always three-part: `` `{{.source_project_name}}.{{.source_dataset_name}}.table` ``

### JOIN Rules

1. **Largest table first**
2. **Explicit ON conditions always**
3. **COALESCE for FULL OUTER JOIN**
4. **No cartesian products**

```sql
-- CORRECT
SELECT COALESCE(a.id, b.id) AS id
FROM large_table a
FULL OUTER JOIN small_table b ON a.id = b.id

-- WRONG
SELECT * FROM a, b WHERE a.id = b.id
```

### Aggregation Rules

```sql
-- ALL non-aggregated columns in GROUP BY
SELECT dev_oid, status, COUNT(*) AS count
FROM dim_ticket
GROUP BY dev_oid, status  -- Both columns listed

-- Filter before aggregation (WHERE not HAVING)
SELECT dev_oid, COUNT(*) AS count
FROM dim_ticket
WHERE status = 'open'  -- Before GROUP BY
GROUP BY dev_oid
```

## Job Configuration Rules

### Required Fields
- `name`: Descriptive job name
- `short_name`: Unique, <=20 chars
- `owners`: Valid email addresses
- `tags`: `"summary"` or `"metrics"`
- `schedule_frequency_in_minutes`: >= 15 minutes

### env_configs Checklist
- [ ] `"local"` entry exists with `config_values`
- [ ] Required config_values: `source_project_name`, `source_dataset_name`, `destination_project_name`, `destination_dataset_name`, `gcs_bucket_name`
- [ ] For metrics jobs: also `aws_s3_bucket_name`
- [ ] Config keys match environment base names

### query_args Checklist
- [ ] Environment keys present for all target environments
- [ ] Template variables in query match query_args keys
- [ ] Values differ between environments where appropriate

### table_creation_config Checklist (only for DELETE+INSERT pattern)

Most jobs use the dummy query pattern and don't need `table_creation_config`. When present:
- [ ] `description` present and non-empty
- [ ] `partition_key` matches an output column
- [ ] `time_partition_type` specified (`"day"` or `"hour"`)

### dataset_config Checklist
- [ ] `name` and `title` set
- [ ] `owner_display_id: "{{.devo_display_id}}"`
- [ ] `create_oasis_dataset: true`
- [ ] `timestamp_column_name` matches time column (if time-partitioned)

### Environment Format
```yaml
# VALID (mixed is fine)
environments: ["local", "dev", "prod.dvrv-us-1"]
environments: ["local", "dev.dvrv-us-1", "qa.dvrv-us-1"]
```

### Query ID Uniqueness
Each query_id must be unique within the job.

## Security Checklist

- [ ] No hardcoded credentials
- [ ] No PII in logs
- [ ] Proper access filtering
- [ ] No sensitive data in error messages

## Pre-Commit Validation

Run before committing:
```bash
python ${CLAUDE_PLUGIN_ROOT}/scripts/validate_job.py <job.yaml>
```
