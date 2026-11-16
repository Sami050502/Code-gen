# Dashboard Development Architecture

**Version:** 2.0.0 (Production)
**Status:** Stable

## Overview

A two-project system for AI-assisted DevRev dashboard and widget creation:

1.  **`dashboard-sync-cli`**: Stable platform interface (Python). Handles all API/Platform interactions.
2.  **`dashboard-dev` plugin**: AI orchestration layer (Claude). Handles logic, generation, and validation.

**Integration**: Plugin shells out to CLI. CLI handles all data normalization and platform communication.

## Core Components

| Component | Role | Key Responsibility |
| :--- | :--- | :--- |
| **CLI** | Platform Interface | API interactions, Auth, Schema Fetching, Data Normalization. |
| **Plugin** | Orchestrator | User Interaction, Workflow Management, Agent Coordination. |
| **Agents** | Generators | `widget-generator` (Widgets), `dashboard-generator` (Assembly). |
| **Skills** | Knowledge Base | `dashboard-planner` (Specs), `dashboard-development`, `widget-development`. |
| **Hooks** | Validators | `PostToolUse` trigger for file writes -> Validation script. |

## Architecture & Data Flow

### 1. Two-Project Split
*   **CLI (`dashboard-sync-cli`)**:
    *   **Path**: `/Users/devrev/Documents/dashboard-sync-cli`
    *   **Function**: Dumb pipe to platform. Reads `.env` for auth.
    *   **Key Ops**: `dataset list`, `dataset fetch`, `widget create`, `dashboard create`.
    *   **Normalization**: `normalize_for_platform()` ensures nested widget refs.
*   **Plugin (`dashboard-dev`)**:
    *   **Path**: `/Users/devrev/Documents/aai-skills/plugins/dashboard-dev`
    *   **Function**: Smart orchestration.
    *   **Strategy**: "Plan -> Generate (Parallel) -> Validate -> Assemble".

### 2. Schema System (On-Demand)
*   **Source**: Oasis TableSchemas API via CLI.
*   **Storage**: Local `datasets/<dataset>.yaml` (No TTL, manual refresh).
*   **Format**: Enriched YAML with UI display names, SQL types, and allowed enum values.
*   **Discovery**:
    *   `devrev.*` (Operational, real-time). **Preferred**.
    *   `dim_*` / `fact_*` (Analytical, require config).

### 3. Workflows

#### A. Dashboard Creation (`/create-dashboard`)
1.  **Plan**: Parse input (Markdown plan or natural language).
2.  **Scaffold**: Create directory structure.
3.  **Discover**: List datasets (CLI).
4.  **Fetch**: JSON schema -> YAML analysis (CLI).
5.  **Sample Data**: Query 10-50 rows to verify schema assumptions (CLI: `dataset query`).
    *   Check field population, actual enum values, JSON structures, time ranges.
    *   Detect sparse fields (>50% NULL), enum mismatches, performance constraints.
    *   Results saved to `datasets/queries/<dataset>_query.json`.
6.  **Generate (Parallel)**: Spin up `widget-generator` for each widget using schema + sample data.
7.  **Validate**: Hook triggers `validate_widget.py` (Structure -> Semantic -> API Dry-Run).
8.  **Assemble**: `dashboard-generator` aggregates validated widgets into Dashboard JSON.
9.  **Deploy**: Upload widgets -> Upload Dashboard -> Sync state.

#### B. Widget Development Skills
The `widget-development` skill provides comprehensive guidance for creating individual widgets, covering:
*   Dataset selection and schema analysis
*   SQL query construction with data sampling
*   Field schema mappings (DevRev ↔ Meerkat)
*   Visualization type selection
*   Validation requirements

#### C. Planning Mode
*   **Tool**: `dashboard-planner` skill.
*   **Output**: Simple Markdown (`plans/*.md`).
*   **Flow**: Map business needs -> `dim`/`fact` tables -> Visualization types.

## Validation Pipeline (3-Stage)

Triggered automatically on file write via `hooks/hooks.json`.

1.  **Structure (<0.1s)**: JSON syntax, required fields (Validator: `mosaic-schema.yaml`).
2.  **Semantic (0.5s)**: Business logic (validators: `field_schema`, `sql`, `viz`, `type_mapping`).
    *   *Critical Rules*: field types, SQL syntax, reference integrity.
3.  **API Dry-Run (1-2s)**: Platform acceptance check.

**Blocking Rules** (Prevent submission):
*   `FIELD_SCHEMA_DISPLAY_NAME_LOCATION`: Must be in `devrev_schema.ui`.
*   `FIELD_SCHEMA_TYPE_VS_FIELD_TYPE`: Use `field_type` (DevRev) vs `type` (Meerkat).
*   `SQL_SCHEMA`: Column access/existence checks.
*   `EMBEDDED_WIDGET_OBJECT`: Detects DOWNLOAD format (embedded widgets) in dashboard.json.

### Validation Logging

All validation activity is logged to workspace `logs/` directory:

```
logs/
├── cli.log                      # CLI operations (rotating, 50MB max)
├── validation-errors.jsonl      # Widget validation (JSONL format)
├── validation-dashboard.jsonl   # Dashboard validation (JSONL format)
└── validation-hooks.log         # Hook script output
```

**Log Viewing**:
```bash
# Real-time validation monitoring
tail -f logs/validation-hooks.log

# Parse structured validation logs
jq 'select(.final_result == "invalid")' logs/validation-errors.jsonl

# Search CLI operations
grep -i "error" logs/cli.log
```

**Log Rotation**: Automatic at 50MB (keeps 5 backups). Configure via `VALIDATION_LOG_MAX_SIZE_MB` and `VALIDATION_LOG_MAX_ROTATED` env vars.

## Data Validation Strategy (Schema + Reality)

**Problem**: Schema metadata alone causes runtime failures (empty results, timeouts, NULL-dominated visualizations).

**Solution**: Proactive data sampling bridges gap between schema structure and data reality.

### Schema vs. Data Reality

| Aspect | Schema Provides | Data Sampling Reveals | Impact Without Sampling |
| :--- | :--- | :--- | :--- |
| **Field Values** | Type definition | Actual enum values, NULL rates | Filters return empty results |
| **Coverage** | Field exists | 68% NULL, orphaned IDs | Grouped charts show mostly NULL |
| **JSON Structure** | Type: json | Actual paths, missing keys | JSON extraction fails |
| **Time Range** | Type: timestamp | MIN: 2024-03-15 (10 months) | 12-month filter returns partial data |
| **Performance** | Table name | 45M rows → timeout without filter | Unfiltered queries fail at runtime |
| **Distribution** | Type: double | MAX: 86400 (outlier skews AVG) | Meaningless aggregations |

### Sampling Integration Points

1.  **Command Level** (`/create-dashboard` workflow): Mandatory sampling before agent invocation.
2.  **Agent Level** (`widget-generator` Process Step 2): Agent verifies data before generation.
3.  **Skill Level** (`widget-development` Data Sampling section): Comprehensive sampling workflow.

### Sample Analysis Checklist

*   Field population: <50% NULL for dimensions.
*   Enum accuracy: Use actual values from data, not schema assumptions.
*   JSON path validity: Verify paths exist, handle missing with COALESCE.
*   Foreign key coverage: >80% coverage for JOINs.
*   Performance constraints: Large tables (>1M rows) require WHERE filters.

**Output**: `datasets/queries/<dataset>_query.json` (read by agents for data-aware generation).

### Common Data Reality Mismatches

**10 failure scenarios prevented by data sampling**:

1. **Empty Result Sets**: Schema says `priority: ["p0", "p1"]`, data contains `["P0", "CRITICAL", "urgent"]`.
2. **Query Timeouts**: Unfiltered queries on 45M-row fact tables exceed 1.5s limit.
3. **NULL-Dominated Charts**: 68% NULL account_id creates misleading "NULL" category dominance.
4. **JSON Extraction Failures**: 60% missing `$.severity` path in JSON fields.
5. **Type Casting Errors**: `custom_id` field contains "JIRA-456" when casting to INT.
6. **Rolling Window Boundary**: Data starts 2024-03-15, 7-day window incomplete for first week.
7. **Array Index Out of Bounds**: 73% of `tags` arrays are NULL or empty.
8. **Foreign Key Coverage**: Only 32% of tickets have `account_id`, JOIN loses 68% of data.
9. **Aggregation Skew**: MAX response_time 86400s (timeout case) skews AVG to meaninglessness.
10. **COUNT(DISTINCT) in Windows**: Meerkat GROUP BY makes column unavailable in window functions.

## Critical Data Constraints

### 1. Dashboard `CREATE` Format
*   **Strict Hierarchy**: `Dashboard -> Tabs -> Sections (Optional) -> Widgets`.
*   **Forbidden**: Root descriptions, Version fields, Flat layouts.
*   **Grid**: 12-column system (`x` + `width` <= 12).

### 2. Widget Reference Object
**Must be nested**:
```json
{
  "reference_id": "widget_1",
  "widget": { "id": "don:identity:..." } // CORRECT
}
```
*   *Incorrect*: `"widget_id": "..."` (Flat reference).

### 3. Field Schema
**Strict nesting for UI/SQL separation**:
```json
"devrev_schema": {
  "field_type": "enum",
  "ui": { "display_name": "Status" } // Nested UI
},
"meerkat_schema": {
  "sql_expression": "status" // SQL mapping
}
```

## Directory Structure

```text
dashboard-dev/
├── agents/             # Generators (dashboard & widget)
├── commands/           # Orchestrators (create-*, plan)
├── hooks/              # Validation triggers (hooks.json)
├── scripts/            # Logic (fetching, validation, rules)
│   └── widget/rules/   # Semantic validators (sql, viz, fields)
├── skills/             # Instructions (planner, creator)
└── ARCHITECTURE.md     # This file

Note: Dataset schemas stored in workspace's datasets/ directory, not in plugin.
```

## Key Decisions

*   **No Setup Command**: Plugin auto-initializes. Validates environment on fly.
*   **No Pre-fetching**: Schemas fetched only when needed to ensure freshness.
*   **Hook Validation**: Decouples validation from generation. Forces agents to fix their own errors via file feedback loop.
*   **YAML Schemas**: Converted from JSON for better LLM readability/token efficiency.
*   **Skills-First Approach**: Complex workflows (widget creation) moved to skills for better reasoning and orchestration.
*   **Embedded Widget Detection**: Validators check for DOWNLOAD format (embedded widgets) vs CREATE format (ID-only refs).

## Common Pitfalls & Fixes

### Pitfall 1: Embedded Widget Objects (DOWNLOAD Format)

**Problem**: Dashboard.json contains full widget objects instead of ID references.

**Symptoms**:
- API error 400: `"Invalid field: description"` (in widget)
- API error 400: `"Invalid field: data_sources"` (in widget)
- API error 400: `"Unexpected JSON type for field: 'widget', expected: 'STRING'"`

**Root Cause**: Using downloaded dashboard as template copies embedded widgets.

**Fix**: Use flat string ID references:
```json
// ✓ CORRECT (CREATE format - flat string)
{"widget": "don:identity:dvrv-us-1:devo/ORG:widget/W-123"}

// ✗ WRONG (nested object with only ID)
{"widget": {"id": "don:..."}}

// ✗ WRONG (DOWNLOAD format - embedded full object)
{"widget": {"title": "...", "data_sources": [...], "id": "..."}}
```

**Prevention**: Validators now detect embedded fields and block with clear error.

### Pitfall 2: Nested Widget References

**Problem**: Using nested `{"id": "..."}` object or wrong field name `widget_id`.

**Fix**: Use flat string format (per API requirements):
```json
// ✓ CORRECT (flat string)
{"widget": "don:..."}

// ✗ WRONG (nested object)
{"widget": {"id": "don:..."}}

// ✗ WRONG (wrong field name)
{"widget_id": "don:..."}
```

### Pitfall 3: Path Inconsistency in Agents

**Problem**: Sub-agents assume different working directory than parent.

**Fix**: Always pass explicit working directory context to spawned agents.

### Pitfall 4: Schema-Only Widget Generation

**Problem**: Generating widgets from schema metadata alone causes runtime failures.

**Symptoms**:
- Empty result sets (enum value mismatches)
- Query timeouts (unfiltered large tables)
- NULL-dominated visualizations (sparse fields)
- Multiple validation iterations (2-3 cycles)

**Root Cause**: Schema describes structure/types, not data characteristics (sparsity, actual values, distributions).

**Fix**: Mandatory data sampling before widget generation:
```bash
dashboard-sync dataset query <dataset> --limit 20
```

**Prevention**: Proactive sampling integrated at command/agent/skill levels reduces validation iterations by 60-80%.
