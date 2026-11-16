---
name: validate
description: Validate Ponos job YAML against data team review criteria before commit
argument-hint: "<job_file.yaml> [--fix]"
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
  - AskUserQuestion
---

# Validate Command

Validate Ponos job YAML against the data team's code review criteria before committing.

## Workflow

### Step 1: Read Job File

Read the specified YAML file to validate.

If file not found, ask user for correct path.

### Step 2: Run Automated Validation

Execute the validation script:

```bash
python ${CLAUDE_PLUGIN_ROOT}/scripts/validate_job.py <job_file> --verbose
```

This checks:
- Job metadata (name, short_name, owners, schedule)
- Environment configuration
- Query validation (partition filters, templates, JOINs)
- Publisher configuration

### Step 3: Present Results

Show validation report to user:

```
=== Ponos Job Validation Report ===

ERRORS (critical - must fix):
  [bigquery] No partition filter detected
    Location: job_activities[0].queries[0]
    Suggestion: Add WHERE DATE(created_date) = {{.record_date}}

WARNINGS (should fix):
  [bigquery] SELECT * detected
    Suggestion: Replace with explicit column list

  [bigquery] Hardcoded dataset name
    Suggestion: Use {{.source_dataset_name}}

INFO:
  [schedule] delay_time_in_minutes not set, defaults to 12 hours

SUMMARY:
  Errors: 1
  Warnings: 2
  Info: 1
```

### Step 4: Manual Review

After automated validation, perform additional manual checks by reading the job file:

**BigQuery Optimization:**
- [ ] Partition filter on ALL partitioned tables
- [ ] Date ranges bounded
- [ ] No SELECT *
- [ ] Clustering keys used in WHERE/JOIN/GROUP BY

**Template Variables:**
- [ ] {{.source_dataset_name}} used
- [ ] {{.record_date}} for date filters
- [ ] No hardcoded project/dataset names

**JOINs:**
- [ ] Largest table first
- [ ] Explicit ON conditions
- [ ] COALESCE for FULL OUTER JOINs

**Publishers:**
- [ ] query_id references exist
- [ ] Dataset config complete for camel
- [ ] Proper select_query in exporters

### Step 5: Offer Fixes

If issues found, ask user:
"Would you like me to fix these issues automatically?"

If yes:

**For SELECT *:**
- Read the source table schema
- Replace with explicit column list

**For hardcoded names:**
- Replace `app-devrev-prod.us_east1_devrev` with `{{.source_dataset_name}}`
- Replace hardcoded dates with `{{.record_date}}`

**For missing partition filter:**
- Add WHERE clause with appropriate partition column

Show the proposed changes before applying.

### Step 6: Apply Fixes

If user approves fixes:
- Edit the job file with corrections
- Re-run validation to confirm fixes worked

### Step 7: Final Report

After all fixes applied (or if no fixes needed):

```
=== Validation Complete ===

Status: PASS (ready for commit)
  or
Status: NEEDS ATTENTION (X errors remain)

Next steps:
- Run /dataset-builder:test to run integration tests
- Create PR to ponos repository
```

## Options

- `--fix`: Automatically apply fixes without asking (still shows changes before writing)

## Best Practices Checked

### Critical (Errors)
- Partition filters present
- Query IDs unique
- Required metadata present
- Valid email in owners

### Important (Warnings)
- No SELECT *
- Template variables used
- Bounded date ranges
- COALESCE for FULL OUTER JOINs

### Informational
- delay_time_in_minutes defaults
- Schedule frequency recommendations
- Clustering suggestions
