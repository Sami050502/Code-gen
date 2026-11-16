---
name: update
description: Update existing PaaS jobs or datasets
argument-hint: "[job|dataset] <id_or_name>"
allowed-tools:
  - Bash
  - Read
  - Write
  - AskUserQuestion
---

# Update Command

Update existing PaaS jobs or datasets in DevRev.

## Usage

```
/dataset-builder:update job <job_id>
/dataset-builder:update dataset <dataset_name>
```

## Workflow

### Step 1: Fetch Current Configuration

**For Job:**
```bash
python ${CLAUDE_PLUGIN_ROOT}/scripts/devrev_api.py serengeti.jobs.get \
  --id "<job_id>"
```

**For Dataset:**
```bash
python ${CLAUDE_PLUGIN_ROOT}/scripts/devrev_api.py oasis.dataset.get \
  --name "<dataset_name>"
```

### Step 2: Show Current Configuration

Display the current configuration to the user in a readable format.

### Step 3: Ask What to Update

Ask user what they want to change:
- Job: SQL query, description, input tables, publisher config
- Dataset: Title, description, columns (limited changes)

### Step 4: Generate Updated Configuration

Create the updated JSON payload based on user's requested changes.

### Step 5: Confirm Changes

Show the diff or summary of changes:
```
Changes to be applied:
- Query SQL: <old> → <new>
- Description: <old> → <new>
```

Ask for confirmation before applying.

### Step 6: Apply Update

**Update Job:**
```bash
python ${CLAUDE_PLUGIN_ROOT}/scripts/devrev_api.py serengeti.jobs.update \
  --data '{
    "id": "<job_id>",
    "name": "updated_name",
    "description": "Updated description",
    "queries": [...],
    "publishers": [...]
  }'
```

**Update Dataset:**
```bash
python ${CLAUDE_PLUGIN_ROOT}/scripts/devrev_api.py oasis.dataset.update \
  --data '{
    "name": "<dataset_name>",
    "title": "Updated Title",
    "description": "Updated description"
  }'
```

### Step 7: Verify Update

Fetch the updated configuration and confirm changes were applied.

## What Can Be Updated

### Jobs

| Field | Updatable | Notes |
|-------|-----------|-------|
| `name` | Yes | Job display name |
| `description` | Yes | Job description |
| `queries` | Yes | SQL, input tables, output table |
| `publishers` | Yes | Publisher configuration |

### Datasets

| Field | Updatable | Notes |
|-------|-----------|-------|
| `title` | Yes | Display title |
| `description` | Yes | Description |
| `columns` | Limited | Can add columns, cannot remove or change types |
| `partition_columns` | No | Cannot change after creation |

**Note:** Partition configuration cannot be changed after dataset creation. To change partitioning, delete and recreate the dataset.

## Examples

### Update Job Query
```
/dataset-builder:update job don:data:dvrv-us-1:devo/787:oasis_job/123
```
Then specify: "Change the SQL to filter by status = 'open'"

### Update Dataset Description
```
/dataset-builder:update dataset my_metrics
```
Then specify: "Update the title to 'Daily Metrics Dashboard'"

## Re-executing After Update

After updating a job, you typically want to re-execute it:

```bash
python ${CLAUDE_PLUGIN_ROOT}/scripts/devrev_api.py serengeti.jobs.execute \
  --data '{"id": "<job_id>"}'
```
