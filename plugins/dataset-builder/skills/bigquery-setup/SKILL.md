---
name: BigQuery Setup
description: This skill should be used when the user asks about "BigQuery access", "GCP access", "bq CLI", "gcloud auth", "AWS CLI setup", "kubectl setup", "request data access", or mentions setting up tools for dataset development. Provides guidance for configuring all required tools and access.
version: 1.0.0
---

# BigQuery and Development Environment Setup

## Overview

Creating custom datasets requires access to BigQuery and various development tools. This skill guides through the complete setup process.

## BigQuery Access

### Access Levels

| Environment | Project | Access Type |
|-------------|---------|-------------|
| Dev | `app-devrev-dev` | Default for developers |
| Prod | `app-devrev-prod` | Requires approval |

**Dataset location:** `us_east1_devrev` in both projects

**Example table:** `app-devrev-dev.us_east1_devrev.fact_timeline`

### Requesting Production Access

To access production BigQuery data:

1. **Create issue in Dev0** with:
   - **Subtype:** Cloud Engineering Requests
   - **Part:** Cloud engineering requests
   - **Request field value:** Data Access

2. **Wait for Neptune Bot** comment in Internal Discussion

3. **Provide required information:**
   - Reason for request
   - Tool requesting (BigQuery)
   - Duration needed

4. **Wait for approval** (typically within 1 day)

**Alternative:** Use Neptune direct link:
```
https://neptune.infra.devrev-eng.ai/additional-services/data-access
```

## Google Cloud SDK Setup

### Installation

**macOS:**
```bash
brew install --cask google-cloud-sdk
```

**Or download:** https://cloud.google.com/sdk/docs/install

### Authentication

```bash
# Login to Google Cloud
gcloud auth login

# Set default project (dev)
gcloud config set project app-devrev-dev

# For production (after approval)
gcloud config set project app-devrev-prod

# Verify authentication
gcloud auth list
```

### BigQuery CLI

The `bq` command is included with Google Cloud SDK:

```bash
# Test access
bq ls us_east1_devrev

# Run a query
bq query --use_legacy_sql=false \
  'SELECT COUNT(*) FROM `app-devrev-dev.us_east1_devrev.dim_ticket` LIMIT 10'

# Get table schema
bq show --schema --format=prettyjson app-devrev-dev:us_east1_devrev.dim_ticket
```

## AWS CLI Setup

Required for Ponos testing environment.

### Installation

**macOS:**
```bash
brew install awscli
```

**Or download:** https://aws.amazon.com/cli/

### SSO Configuration

Create `~/.aws/config` with DevRev profiles:

```toml
[default]
sso_session = DevRev
sso_account_id = 020040093233
sso_role_name = EngineeringDevAccess
region = us-east-1

[sso-session DevRev]
sso_start_url = https://d-9067645937.awsapps.com/start
sso_region = us-east-1
sso_registration_scopes = sso:account:access

[profile dev]
sso_session = DevRev
sso_account_id = 020040093233
sso_role_name = EngineeringDevAccess
region = us-east-1

[profile qa]
sso_session = DevRev
sso_account_id = 990737956189
sso_role_name = EngineeringQAAccess
region = us-east-1

[profile prod-1]
sso_session = DevRev
sso_account_id = 087878894592
sso_role_name = EngineeringProdAccess
region = us-east-1
```

### Login

```bash
# Login with profile
aws sso login --profile dev

# Verify identity
aws sts get-caller-identity --profile dev
```

## kubectl Setup

Required for Ponos integration tests.

### Installation

**macOS:**
```bash
brew install kubectl
```

**Or download:** https://kubernetes.io/docs/tasks/tools/#kubectl

### EKS Configuration

```bash
# Set AWS profile
export AWS_PROFILE=dev

# Verify cluster access
aws eks list-clusters

# Configure kubeconfig
aws eks --region us-east-1 update-kubeconfig --name dev-cluster-2 --alias dev-cluster-2

# Verify connection
kubectl get namespaces
```

## Python Environment

### Required Packages

```bash
pip install requests pyyaml
```

### Virtual Environment (recommended)

```bash
python3 -m venv venv
source venv/bin/activate
pip install requests pyyaml
```

## DevRev PAT Configuration

### Create PAT

1. Go to DevRev Settings > Developer Settings
2. Create Personal Access Token
3. Copy the token

### Configure .env

Create `.env` file in project root:

```bash
DEVREV_PAT=your_token_here
```

The plugin auto-detects environment from PAT:
- `https://auth-token.dev.devrev-eng.ai/` → Dev
- `https://auth-token.devrev.ai/` → Prod
- `https://auth-token.qa.devrev-eng.ai/` → QA

### Verify Configuration

```bash
python ${CLAUDE_PLUGIN_ROOT}/scripts/pat_decoder.py
```

## Shared Repository

Required for Ponos role assumption:

```bash
git clone https://github.com/devrev/shared.git ~/DevRev/shared
```

## Prerequisites Check

Run the check script to verify all tools:

```bash
bash ${CLAUDE_PLUGIN_ROOT}/scripts/check_prerequisites.sh
```

**Expected output:**
```
REQUIRED TOOLS:
  [OK] python: Python 3.x.x
  [OK] gcloud: Google Cloud SDK x.x.x
  [OK] bq: x.x.x
  [OK] aws_cli: aws-cli/2.x.x
  [OK] kubectl: v1.x.x
  [OK] git: git version 2.x.x

CONFIGURATION:
  [OK] aws_config: exists
  [OK] devrev_pat: configured
  [OK] gcloud_auth: authenticated
  [OK] aws_sso_login: authenticated
  [OK] kubectl_context: dev-cluster-2
```

## Troubleshooting

### gcloud auth issues

```bash
# Re-authenticate
gcloud auth revoke --all
gcloud auth login
```

### AWS SSO token expired

```bash
aws sso login --profile dev
```

### kubectl context issues

```bash
# List contexts
kubectl config get-contexts

# Switch context
kubectl config use-context dev-cluster-2
```

### PAT not recognized

```bash
# Verify .env file exists and is formatted correctly
cat .env

# Test PAT decoding
python ${CLAUDE_PLUGIN_ROOT}/scripts/pat_decoder.py
```

## Additional Resources

### Reference Files

- **`references/aws-config.md`** - Full AWS config file template

### Scripts

- **`${CLAUDE_PLUGIN_ROOT}/scripts/check_prerequisites.sh`** - Verify all tools
- **`${CLAUDE_PLUGIN_ROOT}/scripts/pat_decoder.py`** - Test PAT configuration
