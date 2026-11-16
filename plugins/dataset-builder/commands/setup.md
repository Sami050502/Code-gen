---
name: setup
description: Check and configure prerequisites for dataset development (BigQuery, AWS CLI, kubectl, DevRev PAT)
argument-hint: "[--check-only]"
allowed-tools:
  - Bash
  - Read
  - Write
  - AskUserQuestion
---

# Setup Command

Check and configure all prerequisites required for custom dataset development.

## Workflow

### Step 1: Run Prerequisites Check

Execute the check script to identify missing tools:

```bash
bash ${CLAUDE_PLUGIN_ROOT}/scripts/check_prerequisites.sh
```

Collect results for all prerequisites:
- python3
- gcloud CLI
- bq CLI
- AWS CLI
- kubectl
- git
- Python requests library
- AWS config file
- DevRev PAT
- gcloud authentication
- AWS SSO login
- kubectl context

### Step 2: Report Status

Present results to user showing:
- What is properly configured
- What is missing or needs attention

Format as a clear checklist with [OK] or [MISSING] indicators.

### Step 3: Guide Through Missing Items

For each missing prerequisite, provide guidance:

**If gcloud/bq missing:**
- Provide installation command: `brew install --cask google-cloud-sdk`
- Link to download page

**If gcloud not authenticated:**
- Run: `gcloud auth login`
- Set project: `gcloud config set project app-devrev-dev`

**If DevRev PAT missing:**
- Ask user to create PAT in DevRev Settings > Developer Settings
- Create .env file with: `DEVREV_PAT=<token>`
- Verify with pat_decoder.py

**If AWS CLI missing:**
- Provide installation command: `brew install awscli`

**If AWS config missing:**
- Show the full config template from bigquery-setup skill
- Offer to create ~/.aws/config

**If AWS SSO not logged in:**
- Run: `aws sso login --profile dev`

**If kubectl missing:**
- Provide installation: `brew install kubectl`

**If kubectl context missing:**
- Run: `aws eks --region us-east-1 update-kubeconfig --name dev-cluster-2 --alias dev-cluster-2`

### Step 4: Ask About Repository Paths

Ask user for paths to required repositories:
- shared repo (for Ponos role assumption): default `~/DevRev/shared`
- ponos repo (for job files): default `~/DevRev/ponos`

If repos don't exist, provide clone commands.

### Step 5: Verify Complete Setup

Re-run the prerequisites check to confirm all items are now configured.

## Options

If `--check-only` is provided, only run the check script and report results without offering to fix issues.

## Output

End with a summary showing:
- Total prerequisites checked
- Prerequisites configured
- Prerequisites still missing
- Next steps if any issues remain
