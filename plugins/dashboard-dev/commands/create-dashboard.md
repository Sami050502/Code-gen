---
name: dashboard-create
description: Create complete dashboard from business requirements
argument-hint: "[requirement-file.md]"
arguments:
  - name: requirement_file
    description: Path to requirements (plans/*.md or prose file)
    required: true
  - name: output_dir
    description: Output directory for dashboard (default: dashboards/)
    required: false
allowed-tools: Task, Read, Write, Bash, Grep, Glob, AskUserQuestion
---

Create a complete dashboard from a requirements file. Orchestrates widget and dashboard generation through agents, validates all artifacts, and deploys to the platform.

## Input Sources

**Plan files** (from dashboard-planner skill): `plans/<dashboard-slug>.md`
**Prose files**: Any `.md` or `.txt` with free-form requirements

## Phase 1: Parse Requirements

Read requirements: @$1

### Detect Format

**Plan Format** (from dashboard-planner):
- Has `# Dashboard:` title line
- Has `## Widgets` section with numbered widgets
- Each widget has Type, Dataset, Measure fields
- Has `## Organization` table
- Has `## Assumptions` section

**Prose Format** (traditional):
- Free-form text without structured sections
- May mention widgets loosely
- Requires interpretation

### Parse Plan Format

If plan format detected (has structured `## Widgets` section):

1. **Extract dashboard title** from `# Dashboard: [Title]` line
2. **Parse each widget** from numbered sections:
   ```
   ### 1. Widget Name
   - **Type:** metric
   - **Dataset:** devrev.dim_ticket
   - **Measure:** COUNT(*) WHERE status = 'open'
   - **Dimension:** priority (if applicable)
   - **Filter:** condition (if applicable)
   ```

3. **Extract organization** from table:
   ```
   | Tab | Widgets | Purpose |
   |-----|---------|---------|
   | Overview | 1, 2, 3 | Quick health check |
   ```

4. **Construct internal spec**:
   ```json
   {
     "dashboard": {"title": "Support Team Performance"},
     "widgets": [
       {
         "slug": "open-tickets",
         "type": "metric",
         "dataset": "devrev.dim_ticket",
         "description": "COUNT(*) WHERE status = 'open'"
       }
     ],
     "organization": {
       "tabs": [{"name": "Overview", "widgets": [1, 2, 3]}]
     }
   }
   ```

**Plan format advantages:**
- Dataset already specified (skip discovery)
- Widget types pre-selected
- Tab organization defined

### Parse Prose Format

If NO structured sections:

1. **Extract**: Dashboard title, description, purpose
2. **Identify widgets**: Type hints and business descriptions
3. **Note missing**: Datasets, columns need discovery
4. **Flag for discovery**: Widget generators will run dataset list

## Phase 2: Scaffold Folder & Placeholders

Create folder structure:
```bash
SLUG=$(echo "$DASHBOARD_TITLE" | tr '[:upper:]' '[:lower:]' | tr ' ' '-')
mkdir -p dashboards/${SLUG}/widgets
```

Create placeholder files:
```bash
echo '{}' > dashboards/${SLUG}/dashboard.json
for widget in "${WIDGET_SLUGS[@]}"; do
  echo '{}' > dashboards/${SLUG}/widgets/${widget}.json
done
```

Report scaffold:
```
Created: dashboards/${SLUG}/
  ├── dashboard.json
  └── widgets/
      ├── widget-1.json
      └── widget-2.json
```

### Layout Height Guidelines

When positioning widgets, use appropriate heights:
- KPI/Metric cards: height=2
- Charts (line, bar, donut): height=4 minimum
- Full-width charts (width=12): height=5
- Tables: height=6+

**Do NOT use height=3 for charts** - too short for readable visualization.

## Phase 3: Widget Generation (Parallel)

For each widget specification, spawn widget-generator agent.

### From Plan (dataset specified)

```
Task: widget-generator
Prompt: |
  Generate widget: {widget.name}

  Type: {widget.type}
  Dataset: {widget.dataset}
  Measure: {widget.measure}
  Dimension: {widget.dimension}  # if applicable
  Filter: {widget.filter}  # if applicable

  Target file: dashboards/{SLUG}/widgets/{widget.slug}.json

  Steps:
  1. Fetch schema: `dashboard-sync dataset fetch {widget.dataset}`
  2. Build widget JSON using widget-development skill
  3. Write to target file (hook validates automatically)
  4. Iterate until validation passes

  Dataset discovery NOT needed - use provided dataset.
```

### From Prose (dataset discovery needed)

```
Task: widget-generator
Prompt: |
  Generate widget for: {widget.description}

  Target file: dashboards/{SLUG}/widgets/{widget.slug}.json

  Steps:
  1. Discover datasets: `dashboard-sync dataset list`
  2. Fetch schema: `dashboard-sync dataset fetch <dataset>`
  3. Build widget JSON using widget-development skill
  4. Write to target file (hook validates automatically)
  5. Iterate until validation passes
```

Track spawned agents per widget.

## Phase 4: Synchronization Gate

**WAIT**: Do not proceed until ALL widget-generator agents complete.

For each agent:
1. Check completion status
2. Verify validation passed
3. Collect generated file paths

If widget failed:
```
AskUserQuestion:
  question: "Widget '{name}' failed. How to proceed?"
  options:
    - "Skip this widget and continue"
    - "Stop and let me fix manually"
```

## Phase 5: Dashboard Assembly

After widgets validated, spawn dashboard-generator agent:

```
Task: dashboard-generator
Prompt: |
  Generate dashboard JSON.

  Title: {dashboard.title}

  Widget files:
    - dashboards/{SLUG}/widgets/widget-1.json
    - dashboards/{SLUG}/widgets/widget-2.json

  Organization: {organization.tabs}

  Target file: dashboards/{SLUG}/dashboard.json

  Use dashboard-development skill for CREATE format and layout.
```

Wait for completion.

## Phase 6: Platform Deployment

### Create Widgets

For each widget file:
```bash
dashboard-sync widget create dashboards/${SLUG}/widgets/${widget}.json
```

On failure:
1. Parse error message
2. Use widget-development skill to diagnose and fix
3. Retry up to 3 times
4. If still failing, report to user

Collect widget DONs from responses.

### Create Dashboard

```bash
dashboard-sync dashboard create dashboards/${SLUG}/dashboard.json
```

**CRITICAL**: Extract the **full DON ID** from CLI response.
Full DON format: `don:data:dvrv-us-1:devo/{org}:dashboard/{id}`
Do NOT use short ID format in URLs.

On failure:
1. Parse error message
2. Use dashboard-development skill to diagnose and fix
3. Retry up to 3 times
4. If still failing, report to user

## Phase 7: Sync & Report

Sync platform state:
```bash
dashboard-sync dashboard pull ${SLUG}
```

Read URLs from config:
```bash
APP_BASE_URL=$(yq '.platform.app_base_url' config.yaml)
ORG_SLUG=$(yq '.organization.slug' config.yaml)
```

Generate preview URLs (use **full DON ID** from meta.json, NOT short ID):
```
Dashboard Live:    ${APP_BASE_URL}/${ORG_SLUG}/dashboard?dashboardId=${FULL_DASHBOARD_DON}
Dashboard Preview: ${APP_BASE_URL}/${ORG_SLUG}/dashboard-preview?dashboardId=${FULL_DASHBOARD_DON}
Widget Preview:    ${APP_BASE_URL}/${ORG_SLUG}/widget-preview?widgetId=${FULL_WIDGET_DON}
```

**IMPORTANT**: Full DON ID format is `don:data:dvrv-us-1:devo/{org}:dashboard/{id}`
Read the DON from `dashboards/${SLUG}/meta.json` after `dashboard pull` completes.

Report results:
```
## Dashboard Creation Report

Dashboard created successfully

| Resource | Name | Platform ID |
|----------|------|-------------|
| Dashboard | {title} | {dashboard_don} |
| Widget | {name} | {widget_don} |

**Quick Links** (use full DON ID from meta.json):
- 🔗 [View Dashboard]({app_base_url}/{org_slug}/dashboard?dashboardId={full_dashboard_don})
- 🔍 [Preview Dashboard]({app_base_url}/{org_slug}/dashboard-preview?dashboardId={full_dashboard_don})
- 🔍 [Preview Widget]({app_base_url}/{org_slug}/widget-preview?widgetId={full_widget_don})

**Assumptions Made**:
- {list from agents}

**Next Steps**:
- Edit: Modify files in `dashboards/${SLUG}/`
- Push updates: `dashboard-sync dashboard push ${SLUG}`

---

## Recommended: Run Error Detection

Your dashboard is now live! To check for runtime widget errors or UI/UX issues, run the **dashboard-verifier**:

\`\`\`
Check the dashboard at {dashboard_url} for widget errors and UI issues
\`\`\`

This will detect:
- Widget query failures (SQL errors, type mismatches)
- Rendering issues (broken charts, NaN values)
- UI/UX problems (empty widgets, layout issues)
```

## Error Handling

| Phase | Error | Recovery |
|-------|-------|----------|
| Parse | Malformed requirements | Prompt user for clarification |
| Widget Gen | Validation fails 5x | Surface to user, offer skip |
| Deploy | `widget create` fails | Fallback to widget-development skill |
| Deploy | `dashboard create` fails | Fallback to dashboard-development skill |
| Sync | Conflict | Report conflict, suggest `--force` |
