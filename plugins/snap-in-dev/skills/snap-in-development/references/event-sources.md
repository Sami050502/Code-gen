# Event Sources Reference

Complete reference for DevRev snap-in event source types and configurations.

## Event Source Types

| Type | Use Case | Trigger |
|------|----------|---------|
| `devrev-webhook` | DevRev platform events | Work items, conversations, etc. |
| `timer-events` | Scheduled execution | Cron expressions |
| `flow-events` | Programmatic scheduling | Function-triggered |
| `flow-custom-webhook` | External webhooks | HTTP requests with Rego policy |

## devrev-webhook

Listen to events from the DevRev platform.

### Configuration

```yaml
event_sources:
  organization:
    - name: devrev-event-source
      description: Event source listening on DevRev events
      display_name: DevRev Events
      type: devrev-webhook
      config:
        event_types:
          - work_created
          - work_updated
          - ticket_created
          - conversation_created
```

### Available Event Types

#### Work Events
- `work_created` - Any work item created
- `work_updated` - Any work item updated
- `work_deleted` - Any work item deleted

#### Ticket Events
- `ticket_created` - Ticket created
- `ticket_updated` - Ticket updated

#### Issue Events
- `issue_created` - Issue created
- `issue_updated` - Issue updated

#### Conversation Events
- `conversation_created` - Conversation started
- `conversation_updated` - Conversation updated

#### Other Events
- `part_created`, `part_updated` - Part events
- `rev_user_created`, `rev_user_updated` - User events
- `account_created`, `account_updated` - Account events
- `tag_created`, `tag_updated` - Tag events

### With JQ Filter

Filter events before triggering:

```yaml
event_sources:
  organization:
    - name: ticket-only-source
      description: Only ticket events
      display_name: Ticket Events
      type: devrev-webhook
      config:
        event_types:
          - work_updated
        filter:
          jq_query: |
            if .type == "work_updated" then
              if (.work_updated.work.type == "ticket") then true
              else false
              end
            else false
            end
```

### Common Filter Patterns

**Tickets only:**
```jq
if .work_updated.work.type == "ticket" then true else false end
```

**Specific stage change:**
```jq
if .work_updated.work.stage.name == "awaiting_approval" then true else false end
```

**Has specific tag:**
```jq
if (.work_updated.work.tags | map(.id) | contains(["TAG_ID"])) then true else false end
```

## timer-events

Schedule functions to run at specific times using cron expressions.

### Configuration

```yaml
event_sources:
  organization:
    - name: daily-timer
      description: Runs every day at 9 AM UTC
      display_name: Daily Timer
      type: timer-events
      config:
        cron: "0 9 * * *"
```

### Cron Expression Format

```
┌───────────── minute (0-59)
│ ┌───────────── hour (0-23)
│ │ ┌───────────── day of month (1-31)
│ │ │ ┌───────────── month (1-12)
│ │ │ │ ┌───────────── day of week (0-6, Sunday=0)
│ │ │ │ │
* * * * *
```

### Common Cron Patterns

| Pattern | Description |
|---------|-------------|
| `0 * * * *` | Every hour |
| `0 9 * * *` | Daily at 9 AM UTC |
| `0 9 * * 1-5` | Weekdays at 9 AM UTC |
| `*/15 * * * *` | Every 15 minutes |
| `0 0 * * *` | Daily at midnight UTC |
| `0 0 1 * *` | First day of month at midnight |
| `0 9 * * 1` | Every Monday at 9 AM UTC |

### Timer Event Payload

Timer events have minimal payload. Identify via execution_metadata:

```typescript
async function handleTimerEvent(event: FunctionEvent) {
  const eventType = event.execution_metadata.event_type;
  // eventType: "custom:timer_tick" or similar

  // No specific payload data
  // Perform scheduled task
}
```

## flow-events

Programmatically schedule events from within functions.

### Configuration

```yaml
event_sources:
  organization:
    - name: scheduled-events
      description: Programmatically scheduled events
      display_name: Scheduled Events
      type: flow-events
```

### Scheduling Events from Code

```typescript
const SCHEDULER_ENDPOINT = '/internal/event-sources.schedule';

async function scheduleFollowUp(
  event: FunctionEvent,
  payload: any,
  delayMs: number
): Promise<void> {
  const token = event.context.secrets.service_account_token;
  const endpoint = event.execution_metadata.devrev_endpoint;
  const eventSourceId = event.input_data.event_sources['scheduled-events'];

  const body = {
    event_key: `followup_${Date.now()}`,
    event_type: 'custom:follow_up',
    id: eventSourceId,
    payload: Buffer.from(JSON.stringify(payload)).toString('base64'),
    publish_at: new Date(Date.now() + delayMs).toISOString(),
  };

  await axios.post(
    `${endpoint}${SCHEDULER_ENDPOINT}`,
    body,
    {
      headers: {
        Authorization: token,
        'Content-Type': 'application/json',
      },
    }
  );
}
```

### Automation for Flow Events

```yaml
automations:
  - name: handle-scheduled-event
    source: scheduled-events
    event_types:
      - custom:follow_up
    function: process_follow_up
```

## flow-custom-webhook

Receive events from external systems via HTTP webhook with Rego policy processing.

### Basic Configuration

```yaml
event_sources:
  organization:
    - name: external-webhook
      description: Receives external webhook events
      display_name: External Webhook
      type: flow-custom-webhook
      setup_instructions: |
        Use the following URL for your webhook: {{source.trigger_url}}
      config:
        policy: |
          package rego

          output = {"event": event, "event_key": event_key} {
            event := input.request
            event_key := "external_event"
          }
```

### Rego Policy Structure

The policy must define an `output` object:

```rego
package rego

output = {"event": event, "event_key": event_key, "response": response} {
  # Extract event from request
  event := input.request.body
  event_key := "my_event_type"
  response := {
    "status_code": 200,
    "body": "OK"
  }
}
```

### Available Input Fields

```rego
input.request.method      # HTTP method (GET, POST, etc.)
input.request.headers     # Request headers
input.request.body        # Request body (parsed JSON)
input.request.query       # Query parameters
input.request.path        # Request path
```

### Slack Integration Example

```yaml
event_sources:
  organization:
    - name: slack-webhook
      type: flow-custom-webhook
      setup_instructions: |
        Use {{source.trigger_url}} as your Slack Request URL
      config:
        policy: |
          package rego

          status_code := 200

          output = {"event": event, "event_key": event_key} {
            event := input.request
            event_key := "slack_event"
          } else = {"response": response} {
            response := {"status_code": status_code}
          }
```

### HTML Response Example

```yaml
config:
  policy: |
    package rego

    html := `<!DOCTYPE html>
    <html>
    <body>
      <h1>Response Recorded</h1>
      <p>Thank you for your submission.</p>
    </body>
    </html>`

    output = {"event": event, "event_key": event_key, "response": response} {
      input.request.method == "GET"
      event := {"data": input.request.query["data"][0]}
      event_key := "form_response"
      response := {
        "status_code": 200,
        "headers": {
          "Content-Type": "text/html; charset=UTF-8"
        },
        "body": html
      }
    } else = {"response": response} {
      response := {
        "status_code": 401,
        "body": "Unauthorized"
      }
    }
```

### Webhook Payload Access

In function code, external payloads are in `event.payload`:

```typescript
async function handleExternalWebhook(event: FunctionEvent) {
  const externalPayload = event.payload;

  // For Slack
  const slackPayload = externalPayload.body;
  const slackEvent = slackPayload.event;

  // For generic webhook
  const data = externalPayload.data;
}
```

## Automation Patterns

### Single Source, Multiple Events

```yaml
event_sources:
  organization:
    - name: work-events
      type: devrev-webhook
      config:
        event_types:
          - work_created
          - work_updated

automations:
  - name: handle-created
    source: work-events
    event_types:
      - work_created
    function: on_work_created

  - name: handle-updated
    source: work-events
    event_types:
      - work_updated
    function: on_work_updated
```

### Multiple Sources

```yaml
event_sources:
  organization:
    - name: devrev-events
      type: devrev-webhook
      config:
        event_types:
          - ticket_created

    - name: daily-timer
      type: timer-events
      config:
        cron: "0 9 * * *"

    - name: external-webhook
      type: flow-custom-webhook
      config:
        policy: |
          ...

automations:
  - name: handle-tickets
    source: devrev-events
    event_types:
      - ticket_created
    function: on_ticket_created

  - name: daily-report
    source: daily-timer
    event_types:
      - timer_tick
    function: generate_report

  - name: handle-external
    source: external-webhook
    event_types:
      - custom:external_event
    function: on_external_event
```

## Best Practices

### Event Source Naming

- Use descriptive, hyphenated names
- Include the purpose: `ticket-events`, `daily-cleanup-timer`
- Avoid generic names like `source1`

### Filter Optimization

- Apply filters to reduce function invocations
- Use JQ filters for complex conditions
- Test filters with sample payloads

### Webhook Security

- Validate webhook signatures when available
- Use setup_instructions to guide users
- Implement authentication in Rego policies

### Timer Considerations

- Use UTC for all cron expressions
- Account for execution time in scheduling
- Avoid scheduling multiple timers at the same minute
