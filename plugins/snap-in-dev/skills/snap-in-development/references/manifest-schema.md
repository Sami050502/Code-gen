# Manifest Schema Reference (v2)

Complete reference for DevRev snap-in manifest.yaml version 2.

## Top-Level Structure

```yaml
version: "2"                    # Required: Must be "2"
name: "Snap-in Name"           # Required: Display name
description: "Description"      # Required: What the snap-in does

service_account:               # Required: Service account config
  display_name: Bot Name

inputs:                        # Optional: Configuration inputs
  organization: [...]
  user: [...]

event_sources:                 # Optional: Event source definitions
  organization: [...]

functions:                     # Required: Function declarations
  - name: function_name
    description: What it does

automations:                   # Optional: Event-to-function mappings
  - name: automation_name
    source: event_source_name
    event_types: [...]
    function: function_name

hooks:                         # Optional: Lifecycle hooks
  - type: activate
    function: function_name

keyrings:                      # Optional: Secret definitions
  organization: [...]

commands:                      # Optional: Slash commands
  - name: command_name
    ...

snap_kit_actions:              # Optional: UI button actions
  - name: action_name
    ...
```

## Required Fields

### version

```yaml
version: "2"
```

Must be the string `"2"`. Version 1 is deprecated.

### name

```yaml
name: "My Automation Snap-in"
```

Human-readable display name shown in DevRev UI. Use Title Case with spaces.

### description

```yaml
description: "Automates ticket routing based on customer tier"
```

Brief description of what the snap-in does.

### service_account

```yaml
service_account:
  display_name: Automation Bot
```

The service account identity used when the snap-in takes actions.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `display_name` | string | Yes | Name shown for bot actions |

## functions

Declare all functions the snap-in implements.

```yaml
functions:
  - name: on_work_creation
    description: Handles work item creation events

  - name: on_activate
    description: Initialization when snap-in activates
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Function identifier (must match code) |
| `description` | string | Yes | What the function does |

**Naming convention**: Use snake_case, match directory name in `code/src/functions/`.

## inputs

Configuration fields for snap-in users.

### Structure

```yaml
inputs:
  organization:           # Org-level inputs
    - name: input_name
      ...
  user:                   # User-level inputs
    - name: user_input
      ...
```

### Input Field Schema

```yaml
- name: greeting_message
  description: Message displayed to users
  field_type: text
  default_value: "Hello!"
  is_required: true
  ui:
    display_name: Greeting Message
    placeholder: "Enter greeting..."
    is_hidden: false
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Field identifier |
| `description` | string | Yes | Help text |
| `field_type` | string | Yes | Input type (see below) |
| `default_value` | varies | No | Default value |
| `is_required` | boolean | No | Whether required (default: false) |
| `ui` | object | No | UI display options |

### Field Types

| Type | Description | Additional Fields |
|------|-------------|-------------------|
| `text` | String input | - |
| `int` | Integer input | - |
| `bool` | Boolean toggle | - |
| `array` | Multi-value list | `base_type`, `allowed_values` |
| `id` | DevRev object ref | `id_type` |
| `tokens` | Token input | - |

### Array Type

```yaml
- name: business_days
  field_type: array
  base_type: enum
  allowed_values:
    - Monday
    - Tuesday
    - Wednesday
    - Thursday
    - Friday
  default_value:
    - Monday
    - Tuesday
    - Wednesday
    - Thursday
    - Friday
```

### ID Type

```yaml
- name: target_group
  field_type: id
  id_type: group
  ui:
    display_name: Target Group

- name: default_tag
  field_type: id
  id_type: tag
```

Common `id_type` values: `group`, `tag`, `part`, `rev_user`

### UI Options

```yaml
ui:
  display_name: "Human Readable Name"
  placeholder: "Enter value..."
  is_hidden: false
```

| Field | Description |
|-------|-------------|
| `display_name` | Label shown in UI |
| `placeholder` | Placeholder text for inputs |
| `is_hidden` | Hide from UI (for internal state) |

## event_sources

Define where events originate.

```yaml
event_sources:
  organization:
    - name: source_name
      description: Description
      display_name: Display Name
      type: devrev-webhook
      config:
        ...
```

### Common Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Source identifier |
| `description` | string | Yes | Description |
| `display_name` | string | Yes | UI display name |
| `type` | string | Yes | Source type |
| `config` | object | Yes | Type-specific config |

See `references/event-sources.md` for type-specific configurations.

## automations

Connect event sources to functions.

```yaml
automations:
  - name: handle-work-created
    source: devrev-event-source
    event_types:
      - work_created
    function: on_work_creation
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Automation identifier |
| `source` | string | Yes | Event source name reference |
| `event_types` | array | Yes | Events to handle |
| `function` | string | Yes | Function name reference |
| `filter` | object | No | JQ filter for conditional triggering |

### Filter Example

```yaml
automations:
  - name: handle-ticket-only
    source: devrev-event-source
    event_types:
      - work_updated
    function: on_ticket_update
    filter:
      jq_query: |
        if .work_updated.work.type == "ticket" then true else false end
```

## hooks

Lifecycle hooks for initialization and cleanup.

```yaml
hooks:
  - type: activate
    function: on_activate

  - type: deactivate
    function: on_deactivate
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `type` | string | Yes | Hook type (`activate`, `deactivate`) |
| `function` | string | Yes | Function name reference |

## keyrings

Define secrets and API keys.

```yaml
keyrings:
  organization:
    - name: api_token
      description: External API authentication token
      types:
        - snap_in_secret
      display_name: API Token

    - name: slack_token
      description: Slack bot OAuth token
      types:
        - snap_in_secret
      display_name: Slack Token

    - name: sendgrid_key
      types:
        - sendgrid
      display_name: SendGrid API Key
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Keyring identifier |
| `description` | string | No | Description |
| `types` | array | Yes | Secret types |
| `display_name` | string | Yes | UI display name |

### Secret Types

- `snap_in_secret` - Generic secret
- `sendgrid` - SendGrid API key
- `freshdesk` - Freshdesk credentials
- Other integration-specific types

## commands

Slash commands for DevRev discussions.

```yaml
commands:
  - name: approve
    namespace: devrev
    description: Approve this ticket
    surfaces:
      - surface: discussions
        object_types:
          - ticket
    usage_hint: "/approve - Approve the current ticket"
    function: handle_approve
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Command name (no slash) |
| `namespace` | string | Yes | Namespace (usually `devrev`) |
| `description` | string | Yes | Help text |
| `surfaces` | array | Yes | Where command available |
| `usage_hint` | string | No | Usage example |
| `function` | string | Yes | Handler function |

## snap_kit_actions

UI button/action handlers.

```yaml
snap_kit_actions:
  - name: custom_button
    description: Handles custom button clicks
    function: handle_button

  - name: email_submit
    description: Handles email form submission
    function: handle_email_submit
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Action identifier |
| `description` | string | Yes | Description |
| `function` | string | Yes | Handler function |

## Complete Example

```yaml
version: "2"
name: "Ticket Auto-Router"
description: "Automatically routes tickets based on customer tier"

service_account:
  display_name: Routing Bot

inputs:
  organization:
    - name: enabled
      description: Enable automatic routing
      field_type: bool
      default_value: true
      ui:
        display_name: Enable Auto-Routing

    - name: premium_group
      description: Group for premium customers
      field_type: id
      id_type: group
      is_required: true
      ui:
        display_name: Premium Support Group

event_sources:
  organization:
    - name: ticket-events
      description: Ticket creation events
      display_name: Ticket Events
      type: devrev-webhook
      config:
        event_types:
          - ticket_created

functions:
  - name: route_ticket
    description: Routes ticket to appropriate group

  - name: on_activate
    description: Initialization on activation

automations:
  - name: route-new-tickets
    source: ticket-events
    event_types:
      - ticket_created
    function: route_ticket

hooks:
  - type: activate
    function: on_activate
```
