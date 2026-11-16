# Dataset Builder Plugin - Claude Code Guidance

## Plugin Purpose

Help DevRev users create custom datasets using either:
- **Ponos jobs**: YAML-based, cross-org, scheduled via ponos repo
- **PaaS (Ponos as a Service)**: API-based, org-specific, easier setup

## Key Workflows

### 1. Dataset Creation Decision Tree

```
User wants custom dataset
    │
    ├─► Cross-org data needed? ──► YES ──► Ponos
    │
    └─► Org-specific only? ──► YES ──► PaaS
```

### 2. PaaS Workflow (Simpler)

1. Design dataset schema
2. Create dataset via `oasis.dataset.create` API
3. Create job via `serengeti.jobs.create` API
4. Execute job via `serengeti.jobs.execute` API
5. Check status via `jobs.get` API

### 3. Ponos Workflow (More Complex)

1. Design dataset schema
2. Generate YAML job config
3. Validate against review criteria
4. Test locally:
   - AWS SSO login
   - Role assumption
   - `make int-test --bqdryrun`
   - Port-forward services if needed
   - `make int-test` (full)
5. Commit to ponos repo
6. Create PR

## API Endpoints

### DevRev APIs (use PAT from .env)

Environment auto-detected from PAT issuer:
- Dev: `https://api.dev.devrev-eng.ai`
- Prod: `https://api.devrev.ai`
- QA: `https://api.qa.devrev-eng.ai`

**Dataset APIs:**
- `GET /internal/oasis.dataset.list` - List datasets
- `GET /internal/oasis.dataset.get?name={name}` - Get dataset
- `POST /internal/oasis.dataset.create` - Create dataset

**PaaS Job APIs:**
- `POST /internal/serengeti.jobs.create` - Create job
- `POST /internal/serengeti.jobs.execute` - Execute job
- `GET /internal/serengeti.jobs.get?id={id}` - Get job
- `GET /internal/serengeti.jobs.list` - List jobs
- `POST /internal/serengeti.jobs.update` - Update job
- `POST /internal/serengeti.jobs.delete` - Delete job
- `POST /internal/oasis.dataset.delete` - Delete dataset

**Job Status:**
- `GET /internal/jobs.get?id={job_status_id}` - Check execution status

## Managing Jobs & Datasets

### List Jobs
```bash
python ${CLAUDE_PLUGIN_ROOT}/scripts/devrev_api.py serengeti.jobs.list
```

### Update Job
```bash
python ${CLAUDE_PLUGIN_ROOT}/scripts/devrev_api.py serengeti.jobs.update \
  --data '{"id": "...", "name": "new_name", "queries": [...]}'
```

### Delete Job
```bash
python ${CLAUDE_PLUGIN_ROOT}/scripts/devrev_api.py serengeti.jobs.delete \
  --data '{"id": "don:data:...:oasis_job/123"}'
```

### Update Dataset
```bash
python ${CLAUDE_PLUGIN_ROOT}/scripts/devrev_api.py oasis.dataset.update \
  --data '{"name": "dataset_name", "title": "New Title"}'
```
**Note:** Cannot change partition_columns after creation.

### Delete Dataset
```bash
python ${CLAUDE_PLUGIN_ROOT}/scripts/devrev_api.py oasis.dataset.delete \
  --data '{"name": "dataset_name"}'
```

Use `/dataset-builder:update` or `/dataset-builder:delete` commands, or `job-manager` agent for guided management.

## Dataset Discovery

Use `/dataset-builder:explore` to discover available datasets:

```bash
# List known stock datasets (default)
python ${CLAUDE_PLUGIN_ROOT}/scripts/dataset_discovery.py sources

# Query Oasis API for all datasets
python ${CLAUDE_PLUGIN_ROOT}/scripts/dataset_discovery.py oasis

# List BigQuery tables
python ${CLAUDE_PLUGIN_ROOT}/scripts/dataset_discovery.py bigquery

# Get schema for a specific table
python ${CLAUDE_PLUGIN_ROOT}/scripts/dataset_discovery.py schema fact_ticket

# Get recommendations for a use case
python ${CLAUDE_PLUGIN_ROOT}/scripts/dataset_discovery.py recommend "ticket metrics by account"
```

**Important:**
- **fact_* tables**: Primary sources for aggregation (time-partitioned)
- **dim_* tables**: For JOIN enrichment only (already in Oasis)
- Custom datasets should NOT use `dim_` or `fact_` prefixes

## BigQuery Tables

**Location**: `us_east1_devrev` dataset in:
- Dev: `app-devrev-dev`
- Prod: `app-devrev-prod`

**Primary sources (fact_*):**
- `fact_ticket` - Ticket events over time
- `fact_events` - Platform events
- `fact_timeline` - Timeline events
- `fact_issue` - Issue events
- `fact_conversation` - Conversation metrics

**JOIN enrichment (dim_*):**
- `dim_ticket`, `dim_account`, `dim_revu`, `dim_devu`, `dim_issue`, etc.
- Note: dim_* are directly usable in Oasis - no custom dataset needed

## Scripts Usage

All scripts in `${CLAUDE_PLUGIN_ROOT}/scripts/`:

- `dataset_discovery.py` - Discover datasets from Oasis/BigQuery
- `stock_datasets.py` - Hardcoded stock dataset definitions
- `pat_decoder.py` - Decode PAT to get environment (auto-cleans tokens)
- `devrev_api.py` - Make authenticated API calls
- `job_status.py` - Poll job status until completion
- `check_prerequisites.sh` - Verify tool installations
- `setup_ponos_env.sh` - AWS SSO + role assumption
- `port_forward.sh` - kubectl port-forward for testing
- `validate_job.py` - Validate YAML against review criteria

### Job Status Polling

After executing a job, poll until completion:
```bash
python ${CLAUDE_PLUGIN_ROOT}/scripts/job_status.py "don:core:...:job/123" --poll
```

## PaaS vs Ponos Query Syntax

**PaaS queries** use different syntax from Ponos:
- Table names only (no project/dataset prefix): `FROM \`fact_ticket\``
- `@param` syntax for parameters: `@scheduled_at` instead of `{{.agg_start_date}}`
- Auto-scoped to the calling org's `dev_oid` (no manual filtering needed)
- Use `transient_output_table` and `@output` for publisher references

**Ponos queries** use Go templates:
- Three-part FROM: `` `{{.source_project_name}}.{{.source_dataset_name}}.table` ``
- `{{.variable}}` for all parameters
- Manual `dev_oid` filtering

## API Notes (Important!)

### oasis.dataset.create

Required fields:
- `name` - Dataset identifier
- `title` - Human-readable title (REQUIRED!)
- `columns` - Array of column definitions

For time-partitioned datasets, partition columns MUST have:
- `"sql": {"type": "TIMESTAMP"}` (not DATE)
- `"devrev_field_type": "timestamp"` (REQUIRED!)

### serengeti.jobs.create

Response format:
```json
{
  "job": {
    "id": "don:data:dvrv-us-1:devo/787:oasis_job/123"
  }
}
```
Note: Response key is `job`, not `oasis_job`.

## PaaS Job Scheduling

PaaS jobs can be scheduled via **DevRev Workflow Builder**:
- **Trigger:** Timer Trigger (set cron/interval)
- **Action:** Execute Analytics Job (set job ID)
- The `@scheduled_at` parameter receives the trigger timestamp

## Important Reminders

1. **Always ask for repo paths** - Don't assume locations for shared/ponos repos
2. **Show before write** - Always show generated YAML/JSON before writing files
3. **Validate before commit** - Run validation against review criteria
4. **PAT in .env** - Never hardcode tokens, always read from .env
5. **Auto-detect environment** - Use PAT decoder, don't ask user for env
6. **Custom dataset naming** - Do NOT use `dim_` or `fact_` prefixes
7. **Partition columns** - Must use TIMESTAMP type with devrev_field_type
