# Dataset Builder Plugin

Create custom datasets in DevRev using **Ponos jobs** (cross-org) or **PaaS** (org-specific).

## Features

- **Guided Dataset Creation**: Interactive workflow to design and create custom datasets
- **BigQuery Integration**: Query and explore data in BigQuery via `bq` CLI
- **PaaS API Integration**: Direct API calls to create and execute org-specific jobs
- **Ponos Job Generation**: Generate YAML job configs with proper structure
- **Automated Testing**: Run Ponos integration tests with automatic setup
- **Pre-commit Validation**: Validate jobs against DevRev data team review criteria

## Prerequisites

### Required Tools

1. **Google Cloud SDK** (`gcloud` and `bq` CLI)
   - Install: https://cloud.google.com/sdk/docs/install
   - Auth: `gcloud auth login`

2. **AWS CLI** (for Ponos testing)
   - Install: https://aws.amazon.com/cli/
   - Configure SSO: See setup command

3. **kubectl** (for Ponos testing)
   - Install: https://kubernetes.io/docs/tasks/tools/#kubectl

4. **Python 3.8+** (for scripts and API calls)

### BigQuery Access

To access production BigQuery data, create an issue in Dev0:
- **Subtype**: Cloud Engineering Requests
- **Part**: Cloud engineering requests
- **Request field**: Data Access

Without approval, you'll have access to dev only:
- Dev: `app-devrev-dev.us_east1_devrev`
- Prod: `app-devrev-prod.us_east1_devrev` (requires approval)

## Setup

### 1. Create `.env` file in your project root:

```bash
DEVREV_PAT=your_personal_access_token_here
```

The plugin automatically detects your environment (dev/prod/qa) from the PAT token.

### 2. Run setup command:

```bash
/dataset-builder:setup
```

This checks all prerequisites and guides you through any missing configuration.

## Commands

| Command | Description |
|---------|-------------|
| `/dataset-builder:setup` | Check and configure prerequisites |
| `/dataset-builder:explore` | List Oasis datasets, query BQ schemas |
| `/dataset-builder:create` | Create a new dataset (Ponos or PaaS) |
| `/dataset-builder:update` | Update existing jobs or datasets |
| `/dataset-builder:delete` | Delete jobs or datasets |
| `/dataset-builder:test` | Run Ponos job integration tests |
| `/dataset-builder:validate` | Validate job against review criteria |

## When to Use Ponos vs PaaS

| Aspect | Ponos | PaaS |
|--------|-------|------|
| **Scope** | Cross-org (all orgs) | Org-specific |
| **Setup** | YAML in ponos repo + PR | API calls |
| **Scheduling** | Built-in via YAML | Workflow Builder |
| **Use Case** | Stock datasets, metrics | Custom org analytics |
| **Complexity** | Higher | Lower |

## Skills (Auto-activated)

The plugin provides specialized knowledge when you ask about:

- **Dataset concepts**: Oasis platform, dim vs fact, partitioning, clustering
- **Ponos development**: YAML structure, testing, deployment
- **PaaS development**: API usage, job creation and execution
- **BigQuery setup**: Access requests, authentication
- **Ponos best practices**: Code review criteria, BQ optimization

## Project Structure

```
dataset-builder/
├── .claude-plugin/
│   └── plugin.json
├── commands/
│   ├── setup.md
│   ├── explore.md
│   ├── create.md
│   ├── update.md
│   ├── delete.md
│   ├── test.md
│   └── validate.md
├── agents/
│   ├── schema-designer.md
│   ├── query-builder.md
│   ├── job-generator.md
│   ├── job-validator.md
│   ├── job-manager.md
│   └── test-runner.md
├── skills/
│   ├── dataset-concepts/
│   ├── ponos-development/
│   ├── paas-development/
│   ├── bigquery-setup/
│   └── ponos-best-practices/
└── scripts/
    ├── devrev_api.py
    ├── pat_decoder.py
    ├── dataset_discovery.py
    ├── stock_datasets.py
    ├── job_status.py
    ├── check_prerequisites.sh
    ├── setup_ponos_env.sh
    ├── port_forward.sh
    └── validate_job.py
```
