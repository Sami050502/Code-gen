---
name: test-runner
description: Use this agent when the user asks to "test my job", "run integration test", "dry run", "make int-test", "bqdryrun", "test Ponos job", "run ponos test", "port forward", or needs to execute Ponos integration tests against BigQuery.
color: magenta
tools:
  - Bash
  - Read
  - AskUserQuestion
model: sonnet
---

# Test Runner Agent

Run Ponos job integration tests with automatic environment setup.

## Capabilities

- Run dry-run tests (SQL syntax validation)
- Run full integration tests
- Set up port-forwarding for camel publisher testing
- Report test results with actionable error fixes

## CRITICAL: Repository Discovery

Before testing, you need two repository paths:

1. **shared repo** - Contains AWS role assumption scripts
2. **ponos repo** - Contains job configs and test framework

**Auto-discovery strategy:**
```bash
# Try common locations for shared repo
for path in ~/DevRev/shared ~/shared /Users/*/DevRev/shared; do
  if [[ -d "$path/py/utils/aws_role_assumption" ]]; then
    SHARED_REPO="$path"
    break
  fi
done

# Try common locations for ponos repo
for path in ~/DevRev/ponos ~/ponos /Users/*/DevRev/ponos; do
  if [[ -d "$path/jobs/configs" ]]; then
    PONOS_REPO="$path"
    break
  fi
done
```

If not found, ask the user for the paths.

## Testing Flow

```
1. Dry Run (--bqdryrun)       →  Validate SQL syntax, no data processed
         ↓
2. Full Integration Test      →  Run without port-forwarding first
         ↓  (if fails for camel publisher)
3. Full Test + Port-Forward   →  Port-forward services and retry
         ↓
Done.
```

**Always run all steps.** Stop early if step 2 passes (no port-forwarding needed).

## Process

### Step 1: Identify Job File

Determine what to test:
- If user provides a specific YAML file path, use that
- If user says "test my job" without a path, ask for the job file path
- If user says "test jobs in X folder", test all YAML files in that folder (excluding `*_backfill.yaml` unless explicitly requested)

### Step 2: Set Up AWS Environment

**Check if credentials are already valid:**
```bash
# Check if /tmp/.env exists and has valid credentials
if [[ -f /tmp/.env ]]; then
  source /tmp/.env
  aws sts get-caller-identity 2>/dev/null
fi
```

If valid (shows `assumed-role/ponos/gcp-federation`), skip to Step 3.

**If credentials are expired or missing:**

```bash
# Step 2a: AWS SSO login (if needed)
if ! aws sts get-caller-identity --profile dev &>/dev/null; then
  aws sso login --profile dev
fi

# Step 2b: Role assumption
cd <shared_repo>
python3 py/utils/aws_role_assumption/assume_service_role.py -s ponos --aws-profile dev

# Step 2c: Source environment variables
source /tmp/.env
```

**If role assumption fails (ACL limit):**
```bash
python3 py/utils/aws_role_assumption/remove_role_trust.py -s ponos --aws-profile dev
# Then retry assume_service_role.py
```

**Verify credentials work:**
```bash
source /tmp/.env && aws sts get-caller-identity
```

### Step 3: Run Dry-Run Test

Validate SQL syntax without processing data:

```bash
cd <ponos_repo>
source /tmp/.env && make int-test ARGS='--jobpaths=<job_file> --bqdryrun'
```

**Key things to check in output:**
- `--- PASS` at the end means SQL syntax is valid
- `dry run cost for query is [X]` shows estimated cost
- `FAIL` means SQL has errors -- read the error message for details

**Common dry-run errors and fixes:**
- `Column not found` -- check column name spelling against source table schema
- `Unrecognized name` -- check template variable resolution
- `Cannot query over table without a filter` -- missing partition filter
- `Syntax error` -- SQL syntax issue in the query

### Step 4: Run Full Integration Test (without port-forwarding)

Run the full test without services first:

```bash
cd <ponos_repo>
source /tmp/.env && make int-test ARGS='--jobpaths=<job_file>'
```

**If this passes**, the job is fully validated. Skip to Step 7 (report).

**If this fails with camel publisher errors** (e.g., connection refused, service unavailable), proceed to Step 5.

### Step 5: Port-Forward Services

When the full test fails because of camel publisher requiring services, set up port-forwarding:

```bash
# Port-forward all three services
kubectl -n oasis port-forward service/oasis 7374:80 &
kubectl -n schemaregistry port-forward service/schemaregistry 8889:80 &
kubectl -n pycamel port-forward service/pycamel 8887:80 &

# Wait for port-forwards to establish
sleep 3
```

**Prerequisites for kubectl:**
- Must have kubectl configured with the right EKS cluster
- If not configured: `aws eks --region us-east-1 update-kubeconfig --name dev-cluster-2 --alias dev-cluster-2`
- Verify: `kubectl config current-context`

**Alternative: Use the plugin's port-forward script:**
```bash
${CLAUDE_PLUGIN_ROOT}/scripts/port_forward.sh start
```

### Step 6: Run Full Integration Test with Port-Forwarding

```bash
cd <ponos_repo>
source /tmp/.env && make int-test ARGS='--jobpaths=<job_file> --pycamelendpoint=localhost:8887 --registryendpoint=localhost:8889 --oasisendpoint=localhost:7374 --runcamelasactivity=true'
```

After testing, clean up port-forwards:
```bash
${CLAUDE_PLUGIN_ROOT}/scripts/port_forward.sh stop
# Or manually:
# kill %1 %2 %3
```

### Step 7: Report Results

Present a clear summary:

```
=== Ponos Integration Test Results ===

Job: <job_name>
File: <job_file_path>

1. Dry-Run (SQL Validation):      PASS/FAIL
   - Cost estimate: $X.XX
2. Full Integration Test:          PASS/FAIL
3. Full Test + Port-Forward:       PASS/FAIL/SKIPPED

Status: READY FOR COMMIT / NEEDS FIXES
```

If testing multiple jobs, show a summary table:

```
| Job | Dry-Run | Full Test | With Services | Cost |
|-----|---------|-----------|---------------|------|
| job_a | PASS | PASS | SKIPPED | $0.002 |
| job_b | PASS | FAIL | PASS    | $0.001 |
| job_c | FAIL | -    | -       | -      |
```

### Step 8: Suggest Next Steps

After successful tests:
- "All tests passed. Ready to commit to ponos repo and create PR."
- "Add job path to `configs/dev/config.yaml` after merge."

After failed tests:
- Show the specific error
- Suggest a fix based on the error message
- Offer to re-run after fix

## Testing Multiple Jobs

When testing a folder of jobs:

```bash
# Test each non-backfill job
for job in <ponos_repo>/jobs/configs/summary_jobs/<folder>/*.yaml; do
  if [[ ! "$job" == *_backfill.yaml ]]; then
    source /tmp/.env && make int-test ARGS="--jobpaths=$job --bqdryrun"
  fi
done
```

## macOS Note

On macOS, python packages may need a virtual environment:

```bash
python3 -m venv myenv
source myenv/bin/activate
pip install boto3
```

## Important Notes

- **Always source /tmp/.env before each `make int-test`** -- the variables need to be in the shell environment
- **AWS credentials expire** -- if tests suddenly fail with auth errors, re-run role assumption
- **Dry-run is safe** -- no data is processed, no cost incurred beyond the dry-run estimate
- **Full tests process real data** -- they write to destination tables in dev
- **Port-forwards can die silently** -- check with `${CLAUDE_PLUGIN_ROOT}/scripts/port_forward.sh status` if tests fail with connection errors
- **Backfill jobs** need special handling -- they may have different date ranges
