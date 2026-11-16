---
name: test
description: Run Ponos job integration tests with automatic environment setup
argument-hint: "<job_file.yaml> [--dry-run] [--with-services]"
allowed-tools:
  - Bash
  - Read
  - AskUserQuestion
---

# Test Command

Run Ponos job integration tests with automatic environment setup.

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

By default, run all steps (stopping at step 2 if it passes). Use `--dry-run` for step 1 only, `--with-services` to force step 3.

## Workflow

### Step 1: Verify Prerequisites

Check required tools:
- AWS CLI installed
- kubectl installed (for port-forwarding)
- gcloud authenticated

If missing, suggest running `/dataset-builder:setup`.

### Step 2: Discover Repository Paths

Auto-discover shared and ponos repo paths:
```bash
# Try common locations
for path in ~/DevRev/shared ~/shared /Users/*/DevRev/shared; do
  if [[ -d "$path/py/utils/aws_role_assumption" ]]; then
    SHARED_REPO="$path"
    break
  fi
done

for path in ~/DevRev/ponos ~/ponos /Users/*/DevRev/ponos; do
  if [[ -d "$path/jobs/configs" ]]; then
    PONOS_REPO="$path"
    break
  fi
done
```

If not found, ask the user for the paths.

### Step 3: Setup AWS Environment

Check if credentials are already valid:
```bash
if [[ -f /tmp/.env ]]; then
  source /tmp/.env
  aws sts get-caller-identity 2>/dev/null
fi
```

If valid (shows `assumed-role/ponos/gcp-federation`), skip to Step 4.

If not logged in:
```bash
aws sso login --profile dev
```

Then run role assumption:
```bash
cd <shared_repo>
python3 py/utils/aws_role_assumption/assume_service_role.py -s ponos --aws-profile dev
```

If role assumption fails with ACL error:
```bash
python3 py/utils/aws_role_assumption/remove_role_trust.py -s ponos --aws-profile dev
# Retry assume_service_role.py
```

Source environment:
```bash
source /tmp/.env
```

### Step 4: Run Dry-Run Test

Validate SQL syntax without processing data:

```bash
cd <ponos_repo>
source /tmp/.env && make int-test ARGS='--jobpaths=<job_file> --bqdryrun'
```

Report result:
- If passes: "SQL validation successful, cost estimate: $X.XX"
- If fails: Show error and suggest fixes

If `--dry-run` flag was provided, stop here.

### Step 5: Run Full Integration Test

Run full test without port-forwarding:

```bash
cd <ponos_repo>
source /tmp/.env && make int-test ARGS='--jobpaths=<job_file>'
```

If this passes, the job is fully validated. Skip to Step 7.

If this fails with camel publisher errors (connection refused, service unavailable), proceed to Step 6.

### Step 6: Port-Forward Services and Retry

When full test fails because of camel publisher requiring services:

Start port forwards:
```bash
kubectl -n oasis port-forward service/oasis 7374:80 &
kubectl -n schemaregistry port-forward service/schemaregistry 8889:80 &
kubectl -n pycamel port-forward service/pycamel 8887:80 &
sleep 3
```

Re-run with endpoints:
```bash
source /tmp/.env && make int-test ARGS='--jobpaths=<job_file> --pycamelendpoint=localhost:8887 --registryendpoint=localhost:8889 --oasisendpoint=localhost:7374 --runcamelasactivity=true'
```

Clean up after testing:
```bash
kill %1 %2 %3 2>/dev/null
```

### Step 7: Report Results

Summarize test results:

```
=== Ponos Integration Test Results ===

Job: <job_name>

1. Dry-Run (SQL Validation):      PASS/FAIL
   - Cost estimate: $X.XX
2. Full Integration Test:          PASS/FAIL
3. Full Test + Port-Forward:       PASS/FAIL/SKIPPED

Status: READY FOR COMMIT / NEEDS FIXES
```

If all pass:
- "Tests passed! Ready to commit and create PR."

If any fail:
- Show error details
- Suggest fixes based on common issues

### Fallback: Manual Guidance

If automatic setup fails, guide user through manual steps:

1. "Login to AWS SSO manually:"
   ```bash
   aws sso login --profile dev
   ```

2. "Run role assumption from shared repo:"
   ```bash
   cd <shared_repo>
   python3 py/utils/aws_role_assumption/assume_service_role.py -s ponos --aws-profile dev
   source /tmp/.env
   ```

3. "Run test from ponos repo:"
   ```bash
   cd <ponos_repo>
   make int-test ARGS='--jobpaths=<job_file> --bqdryrun'
   make int-test ARGS='--jobpaths=<job_file>'
   ```

## Options

- `--dry-run`: Only run SQL validation (bqdryrun), skip full test
- `--with-services`: Always start port-forward services before testing

## macOS Note

On macOS, python packages may need a virtual environment:
```bash
python3 -m venv myenv
source myenv/bin/activate
pip install boto3
```

## Error Handling

### Common Issues

**AWS SSO expired:**
- Automatically trigger re-login
- Or guide user: `aws sso login --profile dev`

**Role assumption failed (ACL limit):**
- Run cleanup script automatically
- Retry assumption

**kubectl not connected:**
- Run: `aws eks --region us-east-1 update-kubeconfig --name dev-cluster-2 --alias dev-cluster-2`

**Port-forward died silently:**
- Check: `ps aux | grep port-forward`
- Restart port-forwards

**Test timeout:**
- Check for port-forward issues
- Verify AWS credentials haven't expired
