# CLAUDE.md

Claude Code plugin for creating DevRev dashboards and widgets. Orchestrates schema discovery, widget generation, validation, and platform deployment.

## Plugin Structure

```
dashboard-dev/
├── agents/           # Task executors (widget-generator, dashboard-generator)
├── commands/         # Workflow orchestrators (create-dashboard)
├── skills/           # Domain knowledge (widget-development, dashboard-development, dashboard-planner)
├── hooks/            # Validation triggers (PostToolUse on widget/dashboard writes)
├── scripts/          # Utilities (validation rules, schema fetching)
└── docs/             # Reference documentation
```

## Plugin Functionality

### Dashboard Creation Flow

High-level orchestration by `/create-dashboard` command:

1. **Parse** - Extract requirements from plan or prose
2. **Scaffold** - Create `dashboards/<slug>/widgets/` structure
3. **Generate widgets** - Spawn `widget-generator` agents (parallel)
4. **Validate** - Hooks trigger 3-stage validation pipeline
5. **Assemble** - `dashboard-generator` creates `dashboard.json`
6. **Deploy** - CLI uploads to platform, downloads for sync tracking

See `commands/create-dashboard.md` for implementation details.

### Agents

| Agent | Purpose | Invoked By |
|-------|---------|------------|
| `widget-generator` | Generate widget JSON from requirements | `/create-dashboard` command |
| `dashboard-generator` | Assemble dashboard.json with layout | `/create-dashboard` command |

Agents execute autonomously with access to skills and validation scripts.

### Skills

| Skill | Domain | Load When |
|-------|--------|-----------|
| `widget-development` | Widget JSON, SQL, field schemas, data constraints | Creating/fixing widgets |
| `dashboard-development` | Dashboard structure, 12-column grid layouts, CREATE format | Assembling dashboards |
| `dashboard-planner` | Requirements → specifications, dataset selection | Planning from business needs |

Skills contain authoritative patterns. Load the appropriate skill rather than duplicating knowledge.

### Hooks

| Hook | Trigger | Action |
|------|---------|--------|
| `validate-widget-generation` | PostToolUse on `widgets/*.json` writes | Run 3-stage validation pipeline |
| `validate-dashboard-generation` | PostToolUse on `dashboard.json` writes | Validate dashboard structure |

Hooks ensure all generated JSON is validated before deployment.

### Validation

Three-stage pipeline in `scripts/widget/validate_widget.py`:

1. **Structure** - JSON schema validation (must pass)
2. **Semantic** - Business rules in `scripts/widget/lib/rules/`:
   - `structural_rules.py` - Schema constraints, enums, required fields
   - `sql_rules.py` - SQL syntax, column validation, schema discovery
   - `type_mapping_rules.py` - DevRev ↔ Meerkat type mappings
   - `field_schema_rules.py` - Field structure validations
   - `viz_rules.py` - Visualization-specific rules
3. **API** - Platform validation via CLI (final authority)

**Using Coding Agents for Script Development:**

When developing or modifying validation scripts:
- **code-explorer** - Understand existing rule structure
- **code-architect** - Design new validation rules
- **code-reviewer** - Review rule implementations
- **code-simplifier** - Refactor complex validation logic

See `ARCHITECTURE.md` for validation details and common pitfalls.

## Development Workflow

### Use Following Skills While Developing Plugin Components

| Task | Use |
|------|-----|
| Create/modify skills | `plugin-dev:skill-development` skill |
| Create/modify agents | `plugin-dev:agent-development` skill |
| Create/modify commands | `plugin-dev:command-development` skill |
| Create/modify hooks | `plugin-dev:hook-development` skill |
| Review plugin structure | `plugin-dev:plugin-validator` agent |

### Dependent Systems

**Guideline:** While developing skills, explore dependent systems to establish ground truth.

| System | Role | Reference |
|--------|------|-----------|
| **Workspace** | Execution environment (`dashboards/`, `datasets/`) | CLI's workspace-template |
| **CLI** | Platform interaction layer | `/Users/devrev/Documents/dashboard-sync-cli` |
| **Gateway** | Dashboard/widget API | `/Users/devrev/code/explorer/gateway` |
| **Mosaic** | Widget rendering system | `/Users/devrev/code/explorer/dashboard/mosaic` |
| **Mosaic Client** | Schema definitions | `/Users/devrev/code/explorer/dashboard/mosaic-client` |
| **Oasis** | Dataset schema source | API endpoint `/table-schemas.list` |

Use **code-explorer** to navigate these repositories when developing skills that reference platform behavior.

## CLI Integration

Plugin invokes `dashboard-sync` CLI via Bash subprocess for:
- Schema fetching and data sampling
- Widget/dashboard validation
- Platform CRUD operations

See `docs/CLI-REFERENCE.md` for commands.

**CLI Repository:** `/Users/devrev/Documents/dashboard-sync-cli`

## Key Files

- `ARCHITECTURE.md` - Validation pipeline, data constraints, pitfalls
- `hooks/hooks.json` - Validation hook definitions
- `scripts/widget/lib/rules/` - Semantic validation rules
- `scripts/common/` - Shared utilities
