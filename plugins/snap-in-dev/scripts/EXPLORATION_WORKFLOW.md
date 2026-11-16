# Snap-in Exploration Workflow

## Workflow Diagram

```
1. Identify User Intent
   ↓
2. Use useCaseIndex or snapInTypes for broad filtering
   ↓
3. Refine with features/eventTypes/complexity
   ↓
4. Get keyFiles array for each match
   ↓
5. Use Explorer subagent to read:
   - manifest.yaml (structure)
   - Key function files (implementation patterns)
   ↓
6. Extract context with:
   - Absolute file path
   - Relevant lines
   - Summary of relevance
```

---

## Quick Command Reference

### Show Statistics
```bash
npx ts-node ${CLAUDE_PLUGIN_ROOT}/scripts/search-index.ts --stats
```

### Search by Type
```bash
npx ts-node ${CLAUDE_PLUGIN_ROOT}/scripts/search-index.ts --type=event-driven
npx ts-node ${CLAUDE_PLUGIN_ROOT}/scripts/search-index.ts --type=command-based
npx ts-node ${CLAUDE_PLUGIN_ROOT}/scripts/search-index.ts --type=operations
npx ts-node ${CLAUDE_PLUGIN_ROOT}/scripts/search-index.ts --type=timer-based
npx ts-node ${CLAUDE_PLUGIN_ROOT}/scripts/search-index.ts --type=external-webhook
npx ts-node ${CLAUDE_PLUGIN_ROOT}/scripts/search-index.ts --type=hook-based
npx ts-node ${CLAUDE_PLUGIN_ROOT}/scripts/search-index.ts --type=interactive-ui
```

### Search by Keyword
```bash
npx ts-node ${CLAUDE_PLUGIN_ROOT}/scripts/search-index.ts --keyword=slack --limit=5
npx ts-node ${CLAUDE_PLUGIN_ROOT}/scripts/search-index.ts --keyword=ticket --limit=10
npx ts-node ${CLAUDE_PLUGIN_ROOT}/scripts/search-index.ts --keyword=github
```

### Search by Features
```bash
npx ts-node ${CLAUDE_PLUGIN_ROOT}/scripts/search-index.ts --features=keyrings,automation
npx ts-node ${CLAUDE_PLUGIN_ROOT}/scripts/search-index.ts --features=snap-kit-actions
npx ts-node ${CLAUDE_PLUGIN_ROOT}/scripts/search-index.ts --anyFeatures=slack-integration,github-connection
```

### Search by Complexity
```bash
npx ts-node ${CLAUDE_PLUGIN_ROOT}/scripts/search-index.ts --complexity=beginner --limit=10
npx ts-node ${CLAUDE_PLUGIN_ROOT}/scripts/search-index.ts --complexity=intermediate --type=command-based
npx ts-node ${CLAUDE_PLUGIN_ROOT}/scripts/search-index.ts --complexity=advanced --features=operations
```

### Search by Event Type
```bash
npx ts-node ${CLAUDE_PLUGIN_ROOT}/scripts/search-index.ts --eventType=work_created
npx ts-node ${CLAUDE_PLUGIN_ROOT}/scripts/search-index.ts --eventType=work_updated --features=automation
```

### Search by Use Case
```bash
npx ts-node ${CLAUDE_PLUGIN_ROOT}/scripts/search-index.ts --useCase=addSlashCommands
npx ts-node ${CLAUDE_PLUGIN_ROOT}/scripts/search-index.ts --useCase=createInteractiveUI
npx ts-node ${CLAUDE_PLUGIN_ROOT}/scripts/search-index.ts --useCase=receiveExternalWebhooks
npx ts-node ${CLAUDE_PLUGIN_ROOT}/scripts/search-index.ts --useCase=createReusableOperations
```

### Combined Multi-Criteria Search
```bash
npx ts-node ${CLAUDE_PLUGIN_ROOT}/scripts/search-index.ts \
  --type=event-driven \
  --features=keyrings \
  --complexity=intermediate \
  --limit=5
```

---

## Available Options

| Option | Description |
|--------|-------------|
| `--type` | event-driven, command-based, timer-based, external-webhook, operations, hook-based, interactive-ui |
| `--features` | Filter by features (AND logic) |
| `--anyFeatures` | Filter by features (OR logic) |
| `--eventType` | work_created, work_updated, etc. |
| `--complexity` | beginner, intermediate, advanced |
| `--keyword` | Search name, description, id |
| `--useCase` | addSlashCommands, createInteractiveUI, etc. |
| `--learnAbout` | Filter by learning topic |
| `--command` | Filter by command pattern |
| `--operation` | Filter by operation name |
| `--limit` | Max results (default: 10) |
| `--stats` | Show index statistics |
| `--help` | Show help |

---

## Available Use Cases

| Use Case | Description |
|----------|-------------|
| `startNewSnapIn` | Basic templates to start |
| `reactToDevRevEvents` | Event-driven automations |
| `addSlashCommands` | Command-based snap-ins |
| `createInteractiveUI` | Snap Kit actions |
| `receiveExternalWebhooks` | External webhook handlers |
| `schedulePeriodicTasks` | Timer/cron-based tasks |
| `integrateExternalAPIs` | External service integration |
| `supportPerUserConfig` | User-level inputs |
| `validateBeforeDeployment` | Hook-based validation |
| `createReusableOperations` | Operations pattern |

---

## Top Features (for --features filter)

| Feature | Count | Description |
|---------|-------|-------------|
| `automation` | 284 | Has automations |
| `devrev-webhook` | 156 | DevRev event source |
| `commands` | 107 | Slash commands |
| `keyrings` | 93 | Secrets/connections |
| `snap-kit-actions` | 80 | Interactive UI |
| `operations` | 59 | Reusable operations |
| `timer-events` | 52 | Cron scheduling |
| `user-level-inputs` | - | Per-user config |
| `jq-filter` | - | Event filtering |
| `rego-policy` | - | Webhook validation |
