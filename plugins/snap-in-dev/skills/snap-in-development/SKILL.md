---
name: snap-in-development
description: |
  This skill should be used when the user asks about "snap-in manifest", "manifest.yaml structure",
  "snap-in functions", "event sources", "automations", "snap-in hooks", "snap-in inputs",
  "keyrings", "snap_kit_actions", "devrev-webhook", "timer-events", "flow-custom-webhook",
  "flow-events", "function-factory", "service account", "create snap-in", "build snap-in",
  "cron schedule", "rego policy", "TypeScript snap-in", or needs guidance on DevRev snap-in code and
  configuration development. This skill covers manifest structure, functions, event sources,
  automations, inputs, hooks, and keyrings. It does NOT cover local testing, debugging,
  error handling, marketplace deployment, quotas, or upgrade flows.
---

# DevRev Snap-in Development

To develop DevRev snap-ins, configure two main components: the manifest (`manifest.yaml`) declaring configuration, and TypeScript functions in the `code/` directory implementing behavior.

## Snap-in Architecture Overview

A snap-in consists of:

1. **Manifest** (`manifest.yaml`) - Declares the snap-in's configuration, event sources, functions, automations, inputs, and hooks
2. **Code** (`code/`) - TypeScript implementations of declared functions

```
snap-in-project/
├── manifest.yaml           # Configuration
└── code/
    ├── package.json
    ├── tsconfig.json
    └── src/
        ├── function-factory.ts    # Function registry
        └── functions/
            └── {function_name}/
                └── index.ts       # Function implementation
```

## Manifest Structure (v2)

Always use manifest version "2". Required top-level fields:

```yaml
version: "2"
name: "Snap-in Name"
description: "What this snap-in does"

service_account:
  display_name: Bot Name
```

### Core Manifest Sections

| Section | Purpose | Required |
|---------|---------|----------|
| `version` | Manifest version ("2") | Yes |
| `name` | Display name | Yes |
| `description` | Description | Yes |
| `service_account` | Bot identity | Yes |
| `functions` | Function declarations | Yes |
| `event_sources` | Event source definitions | Usually |
| `automations` | Event-to-function mappings | Usually |
| `inputs` | Configuration fields | Optional |
| `hooks` | Lifecycle hooks | Optional |
| `keyrings` | Secret definitions | Optional |
| `commands` | Slash commands | Optional |
| `snap_kit_actions` | UI button actions | Optional |

For complete schema details, see `references/manifest-schema.md`.

## Functions

Functions are the executable units of a snap-in. Declare in manifest:

```yaml
functions:
  - name: on_work_creation
    description: Handles work item creation events
```

Implement in `code/src/functions/{name}/index.ts`:

```typescript
export const run = async (events: any[]) => {
  for (const event of events) {
    const token = event.context.secrets.service_account_token;
    const endpoint = event.execution_metadata.devrev_endpoint;
    // Process event
  }
};

export default run;
```

Register in `code/src/function-factory.ts`:

```typescript
import on_work_creation from './functions/on_work_creation';

export const functionFactory = {
  on_work_creation,
} as const;
```

For detailed function patterns, see `references/function-patterns.md`.

## Event Sources

Event sources define where events originate. Four types available:

| Type | Use Case |
|------|----------|
| `devrev-webhook` | DevRev platform events (work_created, ticket_updated, etc.) |
| `timer-events` | Scheduled/cron-based triggers |
| `flow-events` | Programmatically scheduled events |
| `flow-custom-webhook` | External webhook with Rego policy |

Example devrev-webhook:

```yaml
event_sources:
  organization:
    - name: devrev-event-source
      description: Listens to DevRev events
      display_name: DevRev Events
      type: devrev-webhook
      config:
        event_types:
          - work_created
          - ticket_updated
```

For all event source configurations, see `references/event-sources.md`.

## Automations

Automations connect event sources to functions:

```yaml
automations:
  - name: handle-work-created
    source: devrev-event-source      # References event_sources name
    event_types:
      - work_created
    function: on_work_creation       # References functions name
```

Optional JQ filter for conditional triggering:

```yaml
automations:
  - name: handle-ticket-updates
    source: devrev-event-source
    event_types:
      - work_updated
    function: on_ticket_update
    filter:
      jq_query: |
        if .work_updated.work.type == "ticket" then true else false end
```

## Inputs

Inputs provide configurable fields for snap-in users. Two scopes:

- `organization` - Global settings for the org
- `user` - Per-user settings

### Field Types

| Type | Description |
|------|-------------|
| `text` | String input |
| `int` | Integer input |
| `bool` | Boolean toggle |
| `array` | Multi-value (requires `base_type`) |
| `id` | DevRev object reference (requires `id_type`) |
| `tokens` | Token-based input |

Example:

```yaml
inputs:
  organization:
    - name: greeting_message
      description: Message to display
      field_type: text
      default_value: "Hello!"
      is_required: true
      ui:
        display_name: Greeting Message

    - name: enabled
      field_type: bool
      default_value: true

    - name: target_group
      field_type: id
      id_type: group
      ui:
        display_name: Target Group
```

Access in functions via `event.input_data.global_values.{name}`.

## Hooks

Lifecycle hooks run at specific snap-in events:

```yaml
hooks:
  - type: activate
    function: on_activate

  - type: deactivate
    function: on_deactivate
```

Hook types:
- `activate` - Runs when snap-in is activated (initialization, schema creation)
- `deactivate` - Runs when snap-in is deactivated (cleanup)

## Keyrings

Keyrings store secrets and API keys:

```yaml
keyrings:
  organization:
    - name: api_token
      description: External API token
      types:
        - snap_in_secret
      display_name: API Token

    - name: sendgrid_key
      types:
        - sendgrid
      display_name: SendGrid API Key
```

Access in functions via `event.input_data.keyrings.{name}`.

## Commands and Snap Kit Actions

### Commands (Slash Commands)

```yaml
commands:
  - name: approve
    namespace: devrev
    description: Approve this item
    surfaces:
      - surface: discussions
        object_types:
          - ticket
    usage_hint: "Approve the current ticket"
    function: handle_approve_command
```

### Snap Kit Actions (UI Buttons)

```yaml
snap_kit_actions:
  - name: custom_button
    description: Handle button click
    function: handle_button_click
```

## Quick Reference

### Function Event Structure

```typescript
interface FunctionEvent {
  payload: Record<string, any>;
  context: {
    secrets: { service_account_token: string };
  };
  execution_metadata: {
    devrev_endpoint: string;
    event_type: string;
    function_name: string;
  };
  input_data: {
    global_values: Record<string, any>;
    keyrings: Record<string, string>;
  };
}
```

### Common Event Types

- `work_created`, `work_updated` - Any work item
- `ticket_created`, `ticket_updated` - Tickets specifically
- `conversation_created`, `conversation_updated` - Conversations
- `issue_created`, `issue_updated` - Issues

## Context Gathering from Settings

When providing detailed guidance, check for plugin settings at `.claude/snap-in-dev.local.md`. If configured paths exist (`snap_ins_project_path`, `sdk_source_path`, `examples_path`, `archetype_schemas_path`), use them to find real-world patterns and examples. Reference specific files when providing recommendations. If settings don't exist, use this skill's reference documentation.

## Additional Resources

### Reference Files

For detailed schemas and patterns, consult:

- **`references/manifest-schema.md`** - Complete manifest v2 schema with all fields
- **`references/function-patterns.md`** - Function implementation patterns and SDK usage
- **`references/event-sources.md`** - Event source type configurations and examples

### External Documentation

- [Snap-in Concepts](https://developer.devrev.ai/snapin-development/concepts)
- [Manifest Reference](https://developer.devrev.ai/snapin-development/references/v1-manifest)
- [Functions Reference](https://developer.devrev.ai/snapin-development/references/functions)
- [Inputs Reference](https://developer.devrev.ai/snapin-development/references/inputs)
