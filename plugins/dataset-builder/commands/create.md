---
name: create
description: Create a new custom dataset using Ponos (cross-org) or PaaS (org-specific)
argument-hint: "[ponos|paas]"
allowed-tools:
  - Bash
  - Read
  - Write
  - AskUserQuestion
---

# Create Command

Guide through creating a custom dataset in DevRev using either Ponos or PaaS.

## Workflow

### Step 1: Determine Approach

If argument provided (ponos/paas), use that approach.

Otherwise, ask user:
- "What type of dataset do you need?"
- Options:
  - **Cross-org dataset (Ponos)** - Aggregates data across all organizations
  - **Org-specific dataset (PaaS)** - Data for a single organization only

### Step 2: Gather Requirements

Ask user about the dataset:

1. **Purpose**: "What analytics question will this dataset answer?"
2. **Source data**: "Which existing tables will you aggregate from?"
3. **Refresh frequency**: "How often should this data update?"
4. **Output columns**: "What fields should the final dataset contain?"

### Step 3: Design Schema

Based on requirements, help design the dataset schema:

1. **Dataset name**: Use descriptive names like `ticket_metrics`, `account_summary`. Do NOT use `dim_` or `fact_` prefixes (those are reserved for stock datasets).
2. **Columns**: Define column names and types
3. **Partitioning**:
   - Non-time partitioned: dev_oid only (for current-state snapshots)
   - Time-partitioned: Choose timestamp column and granularity (for historical data)
4. **Clustering**: Suggest clustering columns based on query patterns

Present schema to user for approval.

### Step 4: Write Query

Help construct the BigQuery query:

1. Start with base table(s)
2. Add necessary JOINs
3. Apply filters (especially partition filters)
4. Add aggregations
5. Use template variables ({{.source_dataset_name}}, {{.record_date}})

Validate query follows best practices:
- Partition filter present
- No SELECT *
- Proper JOIN conditions
- Template variables used

### Step 5A: For Ponos

If creating Ponos job:

1. **Generate YAML**:
   - Job metadata (name, short_name, owners)
   - Schedule configuration
   - Query activity
   - Publisher configuration (camel for Oasis)

2. **Show generated YAML** to user

3. **Ask for confirmation**: "Would you like me to write this to the ponos repository?"

4. **If confirmed**, ask for ponos repo path and write file

5. **Suggest next steps**:
   - Run `/dataset-builder:validate` to check against review criteria
   - Run `/dataset-builder:test` to run integration tests

### Step 5B: For PaaS

If creating PaaS job:

1. **Create dataset first** (if doesn't exist):
   ```bash
   python ${CLAUDE_PLUGIN_ROOT}/scripts/devrev_api.py oasis.dataset.create --data '{...}'
   ```

2. **Create job**:
   ```bash
   python ${CLAUDE_PLUGIN_ROOT}/scripts/devrev_api.py serengeti.jobs.create --data '{...}'
   ```

3. **Show job ID** from response

4. **Ask if user wants to execute**:
   - If yes, execute job and monitor status
   - If no, provide command for later execution

### Step 6: Verify Creation

For PaaS:
- Check job status
- Verify dataset has data

For Ponos:
- Remind about testing and PR process

## Output Format

### For Ponos

Show generated YAML with comments explaining each section:
```yaml
name: "descriptive_name"
short_name: "DN"  # Unique identifier
owners: ["email@devrev.ai"]
# ... rest of config
```

### For PaaS

Show:
1. Dataset creation request/response
2. Job creation request/response
3. Job ID for future reference
4. Execution status (if executed)

## Best Practices Applied

Throughout the workflow, ensure:
- Partition filters on all partitioned tables
- Template variables instead of hardcoded values
- Proper column selection (no SELECT *)
- Appropriate refresh frequency
- Cost-efficient query patterns
