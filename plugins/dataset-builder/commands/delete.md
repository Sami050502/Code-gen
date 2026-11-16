---
name: delete
description: Delete PaaS jobs or datasets
argument-hint: "[job|dataset] <id_or_name>"
allowed-tools:
  - Bash
  - Read
  - AskUserQuestion
---

# Delete Command

Delete PaaS jobs or datasets from DevRev.

## Usage

```
/dataset-builder:delete job <job_id>
/dataset-builder:delete dataset <dataset_name>
```

## Workflow

### Step 1: Parse Arguments

Determine what to delete:
- `job <id>` → Delete a PaaS job
- `dataset <name>` → Delete a dataset

### Step 2: Confirm Deletion

**ALWAYS confirm before deleting:**

Ask user: "Are you sure you want to delete [job/dataset] `<id>`? This cannot be undone."

Options:
- Yes, delete it
- No, cancel

### Step 3: Execute Deletion

**Delete Job:**
```bash
python ${CLAUDE_PLUGIN_ROOT}/scripts/devrev_api.py serengeti.jobs.delete \
  --data '{"id": "<job_id>"}'
```

**Delete Dataset:**
```bash
python ${CLAUDE_PLUGIN_ROOT}/scripts/devrev_api.py oasis.dataset.delete \
  --data '{"name": "<dataset_name>"}'
```

### Step 4: Verify Deletion

Confirm the deletion was successful by checking the response.

## Finding Job/Dataset IDs

### List Jobs
```bash
python ${CLAUDE_PLUGIN_ROOT}/scripts/devrev_api.py serengeti.jobs.list
```

### List Datasets
```bash
python ${CLAUDE_PLUGIN_ROOT}/scripts/devrev_api.py oasis.dataset.list
```

## Examples

### Delete a Job
```
/dataset-builder:delete job don:data:dvrv-us-1:devo/787:oasis_job/123
```

### Delete a Dataset
```
/dataset-builder:delete dataset my_custom_dataset
```

## Safety

- Always confirm before deletion
- Deletion is permanent and cannot be undone
- Deleting a dataset does not delete associated jobs (and vice versa)
- Consider listing jobs/datasets first to verify the correct ID
