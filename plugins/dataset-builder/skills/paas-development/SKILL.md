---
name: PaaS Development
description: This skill should be used when the user asks to "create a PaaS job", "org-specific dataset", "serengeti API", "oasis job", "execute analytics job", or mentions on-demand job execution. Provides guidance for creating and executing PaaS (Ponos as a Service) jobs with direct API integration.
version: 1.0.0
---

# PaaS (Ponos as a Service) Development

## Overview

PaaS offers a way to create and execute on-demand jobs for BigQuery aggregation. Compared to Ponos YAML jobs, PaaS is easier to create and better for fast iteration.

**Key characteristics:**
- Jobs are dev-org scoped (one org only)
- Can only aggregate over stock datasets
- Created and managed via REST APIs
- Ideal for org-specific analytics

## When to Use PaaS

| Use Case | Recommendation |
|----------|----------------|
| Org-specific analytics | PaaS |
| Quick prototyping | PaaS |
| Ad-hoc reports | PaaS |
| Cross-org aggregation | Ponos |
| Production stock datasets | Ponos |

## CRITICAL: Time Partitioning

**For historical/event data, ALWAYS use time partitioning!**

| Partitioning | Behavior on Job Run | Use For |
|--------------|---------------------|---------|
| **No partition** | Data REPLACED | Current snapshots only |
| **Time-partitioned** | Data APPENDED per partition | Historical data, events, metrics |

**Without time partitioning, each job run REPLACES all existing data!**

## API Workflow

### Step 1: Create Dataset (if needed)

Before creating a job, ensure the target dataset exists.

**For historical/event data (RECOMMENDED):**

```bash
python ${CLAUDE_PLUGIN_ROOT}/scripts/devrev_api.py oasis.dataset.create \
  --data '{
    "name": "issue_stage_history",
    "title": "Issue Stage History",
    "columns": [
      {"name": "issue_id", "sql": {"type": "VARCHAR"}},
      {"name": "stage_name", "sql": {"type": "VARCHAR"}},
      {"name": "stage_entered_date", "sql": {"type": "TIMESTAMP"}},
      {"name": "record_date", "sql": {"type": "TIMESTAMP"}}
    ],
    "partition_columns": [
      {
        "name": "record_date",
        "sql": {"type": "TIMESTAMP"},
        "devrev_field_type": "timestamp",
        "timestamp_granularity": "month",
        "data_window_granularity": 3
      }
    ]
  }'
```

**For current-state snapshots only (data will be REPLACED each run):**

```bash
python ${CLAUDE_PLUGIN_ROOT}/scripts/devrev_api.py oasis.dataset.create \
  --data '{
    "name": "department_analytics",
    "title": "Department Analytics",
    "columns": [
      {"name": "department", "sql": {"type": "VARCHAR"}},
      {"name": "user_count", "sql": {"type": "BIGINT"}}
    ],
    "partition_columns": []
  }'
```

### Step 2: Create Job

Create the PaaS job definition:

```bash
python ${CLAUDE_PLUGIN_ROOT}/scripts/devrev_api.py serengeti.jobs.create \
  --data '{
    "name": "department_analytics_job",
    "description": "Aggregates rev user count by department",
    "queries": [
      {
        "sql": "SELECT DISTINCT JSON_EXTRACT_SCALAR(r.custom_fields, '\''$.tnt__department'\'') AS department, COUNT(*) AS user_count FROM `dim_revu` AS r WHERE r.is_deleted <> TRUE AND JSON_EXTRACT_SCALAR(r.custom_fields, '\''$.tnt__department'\'') IS NOT NULL GROUP BY 1 ORDER BY user_count DESC",
        "input_tables": ["dim_revu"],
        "transient_output_table": "dim_revu_op"
      }
    ],
    "publishers": [
      {
        "type": "oasis",
        "oasis": {
          "sql": "SELECT * FROM @dim_revu_op",
          "dataset_name": "department_analytics"
        }
      }
    ]
  }'
```

**Response contains the job ID:**
```json
{
  "job": {
    "id": "don:data:dvrv-us-1:devo/787:oasis_job/42401"
  }
}
```

### Step 3: Execute Job

Trigger job execution:

```bash
python ${CLAUDE_PLUGIN_ROOT}/scripts/devrev_api.py serengeti.jobs.execute \
  --data '{"id": "don:data:dvrv-us-1:devo/787:oasis_job/42401"}'
```

**Response:**
```json
{
  "job_status_id": "don:core:dvrv-us-1:devo/787:job/157300"
}
```

### Step 4: Check Status

Monitor execution progress (single check):

```bash
python ${CLAUDE_PLUGIN_ROOT}/scripts/devrev_api.py jobs.get \
  --id "don:core:dvrv-us-1:devo/787:job/157300"
```

**Or poll until completion:**

```bash
python ${CLAUDE_PLUGIN_ROOT}/scripts/job_status.py \
  "don:core:dvrv-us-1:devo/787:job/157300" --poll
```

**Status values:**
- `queued` - Waiting to start
- `in_progress` (progress: 0-99)
- `completed` (progress: 100)
- `failed`

## Job Structure

### Query Configuration

```json
{
  "queries": [
    {
      "sql": "SELECT ... FROM `table_name` WHERE ...",
      "input_tables": ["dim_ticket", "dim_revu"],
      "transient_output_table": "query_output"
    }
  ]
}
```

**Important notes:**
- Use table names directly (no project/dataset prefix)
- `dev_oid` filter is automatic (job is org-scoped)
- Reference transient tables with `@` prefix in publishers

### Publisher Configuration

```json
{
  "publishers": [
    {
      "type": "oasis",
      "oasis": {
        "sql": "SELECT * FROM @transient_table",
        "dataset_name": "target_dataset"
      }
    }
  ]
}
```

### Using Parameters

Pass runtime parameters to queries:

```json
{
  "queries": [{
    "sql": "SELECT * FROM dim_ticket WHERE DATE(modified_date) = @scheduled_at"
  }]
}
```

Execute with parameters:

```bash
python ${CLAUDE_PLUGIN_ROOT}/scripts/devrev_api.py serengeti.jobs.execute \
  --data '{
    "id": "don:data:dvrv-us-1:devo/787:oasis_job/123",
    "parameters": {
      "scheduled_at": "2025-07-21"
    }
  }'
```

## Time-Partitioned Datasets

### Create Partitioned Dataset

**Important:** Partition columns must use `TIMESTAMP` type with `devrev_field_type: "timestamp"`.

```json
{
  "name": "daily_metrics",
  "title": "Daily Metrics",
  "columns": [
    {"name": "total_count", "sql": {"type": "BIGINT"}},
    {"name": "record_date", "sql": {"type": "TIMESTAMP"}}
  ],
  "partition_columns": [
    {
      "name": "record_date",
      "sql": {"type": "TIMESTAMP"},
      "devrev_field_type": "timestamp",
      "timestamp_granularity": "month",
      "data_window_granularity": 3
    }
  ]
}
```

### Create Job with Date Parameter

```json
{
  "name": "daily_metrics_job",
  "queries": [{
    "sql": "SELECT COUNT(DISTINCT id) AS total_count, DATE(@scheduled_at) AS record_date FROM fact_ticket WHERE DATE(created_date) = DATE(@scheduled_at)",
    "input_tables": ["fact_ticket"],
    "transient_output_table": "metrics_output"
  }],
  "publishers": [{
    "type": "oasis",
    "oasis": {
      "sql": "SELECT * FROM @metrics_output",
      "dataset_name": "daily_metrics"
    }
  }]
}
```

## Scheduling PaaS Jobs

Use DevRev Workflow Builder to schedule PaaS jobs:

1. Create PaaS job via API
2. Go to DevRev > Settings > Workflow Builder > New Workflow
3. Add **Timer Trigger** node (cron or interval)
4. Add **Execute Analytics Job** node
   - Select your PaaS job
   - For time-partitioned: use "Scheduled At" variable
5. Connect nodes and deploy

## Common API Errors

### oasis.dataset.create Errors

**Missing title field:**
```json
{"error": "title is required"}
```
Fix: Add `"title": "Human Readable Title"` to dataset definition.

**Invalid partition type:**
```json
{"error": "partition column type must be TIMESTAMP"}
```
Fix: Partition columns must have `"sql": {"type": "TIMESTAMP"}` and include `"devrev_field_type": "timestamp"`.

**Missing devrev_field_type:**
```json
{"error": "devrev_field_type is required for partition columns"}
```
Fix: Add `"devrev_field_type": "timestamp"` to each partition column.

### serengeti.jobs.create Errors

**SQL syntax error:**
Check your SQL for BigQuery-specific syntax. Common issues:
- Use backticks for table names: `` `dim_ticket` ``
- Use `DATE()` and `TIMESTAMP()` functions correctly
- Escape single quotes properly in JSON

### serengeti.jobs.execute Errors

**Invalid job ID:**
The job ID comes from `response.job.id` (not `response.oasis_job.id`).

## Debugging Failed Jobs

When a job fails:

1. **Check status response** for error details
2. **Review logs in Datadog:**
   ```
   @dev_oid:DEV-XXXXXXXXXX service:ponos @oasis_job_id:*<job_id>
   ```
3. **Common issues:**
   - SQL syntax errors
   - Missing input tables
   - Dataset not found
   - Column type mismatches

4. **Fix and retry:**
   ```bash
   # Update job
   python ${CLAUDE_PLUGIN_ROOT}/scripts/devrev_api.py serengeti.jobs.update \
     --data '{"id": "...", "queries": [...]}'

   # Re-execute
   python ${CLAUDE_PLUGIN_ROOT}/scripts/devrev_api.py serengeti.jobs.execute \
     --data '{"id": "..."}'
   ```

## Managing Jobs and Datasets

### List Jobs

```bash
python ${CLAUDE_PLUGIN_ROOT}/scripts/devrev_api.py serengeti.jobs.list
```

### Get Job Details

```bash
python ${CLAUDE_PLUGIN_ROOT}/scripts/devrev_api.py serengeti.jobs.get \
  --id "don:data:dvrv-us-1:devo/787:oasis_job/123"
```

### Delete Job

```bash
python ${CLAUDE_PLUGIN_ROOT}/scripts/devrev_api.py serengeti.jobs.delete \
  --data '{"id": "don:data:dvrv-us-1:devo/787:oasis_job/123"}'
```

### Update Job

```bash
python ${CLAUDE_PLUGIN_ROOT}/scripts/devrev_api.py serengeti.jobs.update \
  --data '{
    "id": "don:data:dvrv-us-1:devo/787:oasis_job/123",
    "name": "updated_job_name",
    "description": "Updated description",
    "queries": [
      {
        "sql": "SELECT ... FROM fact_ticket WHERE ...",
        "input_tables": ["fact_ticket"],
        "transient_output_table": "output"
      }
    ],
    "publishers": [...]
  }'
```

After updating, re-execute the job to apply changes:
```bash
python ${CLAUDE_PLUGIN_ROOT}/scripts/devrev_api.py serengeti.jobs.execute \
  --data '{"id": "don:data:dvrv-us-1:devo/787:oasis_job/123"}'
```

### Update Dataset

```bash
python ${CLAUDE_PLUGIN_ROOT}/scripts/devrev_api.py oasis.dataset.update \
  --data '{
    "name": "my_dataset_name",
    "title": "Updated Title",
    "description": "Updated description"
  }'
```

**Limitations:**
- Can update: title, description, add new columns
- Cannot update: partition_columns (must delete and recreate)

### Delete Dataset

```bash
python ${CLAUDE_PLUGIN_ROOT}/scripts/devrev_api.py oasis.dataset.delete \
  --data '{"name": "my_dataset_name"}'
```

**Note:** Deleting a dataset does not delete jobs that publish to it (and vice versa).

## API Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `serengeti.jobs.create` | POST | Create new job |
| `serengeti.jobs.list` | GET | List all jobs |
| `serengeti.jobs.get` | GET | Get job by ID |
| `serengeti.jobs.update` | POST | Update job |
| `serengeti.jobs.execute` | POST | Execute job |
| `serengeti.jobs.delete` | POST | Delete job |
| `oasis.dataset.delete` | POST | Delete dataset |
| `jobs.get` | GET | Check execution status |

## Additional Resources

### Reference Files

- **`references/paas-examples.md`** - Complete PaaS job examples

### Scripts

- **`${CLAUDE_PLUGIN_ROOT}/scripts/devrev_api.py`** - API client for all operations
- **`${CLAUDE_PLUGIN_ROOT}/scripts/pat_decoder.py`** - Environment detection
