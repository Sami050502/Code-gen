# DevRev Dashboard Development Plugin

Create production-ready dashboard widgets for DevRev's analytics platform with AI-powered assistance.

## Quick Start

### 1. Initialize Workspace

Initialize your workspace with automatic dependency installation:

```bash
cd your-project
dashboard-sync init
```

This command:
- Creates workspace directory structure
- Copies template files
- **Automatically installs plugin dependencies** (pyyaml, jsonschema, sqlglot, duckdb, etc.)

### 2. Set Up Credentials

Create `.env` in your workspace root:

```env
DEVREV_PAT=your-personal-access-token
DEVREV_ENDPOINT=https://api.devrev.ai
```

#### Automatic Workspace Configuration

The plugin automatically generates `config.yaml` when Claude Code launches in a workspace that:
- Has a `.env` file with `DEVREV_PAT` and `DEVREV_ENDPOINT`
- Does not already have a `config.yaml` file

This happens via a SessionStart hook that runs `dashboard-sync config init`.

**Manual Configuration**

If you prefer manual control or need to regenerate the config:
```bash
# Generate config.yaml only (non-destructive, safe for existing workspaces)
dashboard-sync config init

# Full workspace initialization (creates directories and templates)
dashboard-sync init
```

**Troubleshooting Auto-Configuration**

If `config.yaml` is not auto-generated:
1. Check `.env` file exists with correct credentials
2. Verify `dashboard-sync` CLI is installed: `dashboard-sync --version`
3. Run manually: `dashboard-sync config init`

### 3. Plan a Dashboard (Optional)

For vague requirements, use plan mode to generate a structured plan:

```
User: "I need a support dashboard"
→ Claude enters plan mode
→ Discovers relevant datasets (dim_ticket, fact_ticket_stage_transitions)
→ Analyzes schemas and maps fields to visualizations
→ Generates plan: plans/support-team.md
→ User reviews and approves
→ /create-dashboard plans/support-team.md
```

Plans use simple Markdown - no special format needed.

### 4. Create Dashboard

```bash
# From plan file
/create-dashboard plans/support-team.md

# From prose requirements
/create-dashboard ./requirements.txt

# From natural language
/create-dashboard Create a dashboard with ticket counts by priority
```

## Troubleshooting

### Missing Python Dependencies

If you see `ModuleNotFoundError: No module named 'yaml'` (or similar):

**Solution 1 (Recommended):** Re-run workspace init:
```bash
cd <workspace-root>
dashboard-sync init
```

**Solution 2:** Manual installation:
```bash
pip install pyyaml jsonschema sqlglot duckdb requests aiohttp aiofiles pyarrow
```

**Solution 3:** Install from requirements file:
```bash
pip install -r ${CLAUDE_PLUGIN_ROOT}/scripts/widget/requirements.txt
```

The validation pipeline will detect missing dependencies and provide these instructions automatically.

## How It Works

The `/create-dashboard` command:

1. Parses your requirements (from plan file or natural language)
2. Discovers available datasets from platform
3. Fetches schemas from authoritative Oasis API
4. Samples data to verify schema assumptions and data quality
5. Scaffolds dashboard directory structure
6. Launches widget-generator agents in parallel (one per widget)
7. Assembles validated widgets into dashboard structure

### Validation Loop

When widget-generator writes to `widgets/*.json`, a **PostToolUse hook** automatically triggers 3-stage validation:

1. Structure validation (JSON schema)
2. Semantic validation (business rules)
3. API validation (DevRev server)

Errors are fed back to the generator for automatic fixes (max 3 attempts). All validation activity is logged to `logs/` directory for debugging and monitoring.

## Commands

| Command | Description |
|---------|-------------|
| `/create-dashboard [requirements-file]` | Create complete dashboard from business requirements |

## Widget Types

| Type | Use Case |
|------|----------|
| Table | Detailed data display |
| Bar Chart | Category comparison |
| Line Chart | Trends over time |
| Donut Chart | Part-of-whole |
| Metric | Single KPI number |

## Example Prompts

```bash
# Support dashboard
/create-dashboard Create a dashboard with ticket counts by state, priority distribution, and trends

# Customer success dashboard
/create-dashboard Create a dashboard showing conversations by channel and account engagement

# Product analytics
/create-dashboard Create a dashboard with issue counts by priority over the last 30 days
```

## File Structure

```
your-project/
├── .env                     # DevRev credentials
├── datasets/                # Dataset schemas (*.yaml files) and query results
├── plans/                   # Dashboard plan files (*.md)
├── dashboards/              # Dashboard output directories
│   └── <dashboard-name>/
│       ├── dashboard.json   # Dashboard structure
│       └── widgets/         # Widget JSON files
└── logs/                    # Validation logs
```

## Dataset Schema Management

100+ datasets available. Use the CLI for schema operations:

```bash
# List all available datasets
dashboard-sync dataset list --scope all

# Fetch specific schema
dashboard-sync dataset fetch dim_ticket

# Query sample data
dashboard-sync dataset query dim_ticket --limit 10
```

## Architecture

See [ARCHITECTURE.md](ARCHITECTURE.md) for comprehensive technical documentation:
- **System Overview**: Two-project architecture (CLI + Plugin)
- **Components**: 2 commands, 2 agents, 3 skills
- **Workflows**: Widget creation, dashboard generation, planning mode
- **Validation Pipeline**: 3-stage validation (Structure → Semantic → API)
- **Schema System**: On-demand fetching from Oasis API
- **Critical Formats**: Dashboard CREATE payloads, widget references, field schemas
- **Implementation Details**: Hook-driven automation, parallel agent execution
- **Troubleshooting**: Common pitfalls and solutions

---

**Version:** 2.0.0 | **Author:** DevRev Applied AI Team
