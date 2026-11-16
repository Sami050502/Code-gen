# Function Implementation Patterns

Detailed patterns for implementing DevRev snap-in functions in TypeScript.

## Function Structure

### File Organization

```
code/src/
├── functions/
│   └── {function_name}/
│       └── index.ts        # Main function implementation
├── function-factory.ts     # Function registry
└── index.ts               # Exports
```

### Standard Function Signature

```typescript
// code/src/functions/on_work_creation/index.ts

export const run = async (events: any[]): Promise<void> => {
  for (const event of events) {
    await handleEvent(event);
  }
};

export default run;
```

**Requirements:**
- Export `run` function (as named export or default)
- Accept events array parameter
- Process events in loop

## Event Interface

### Complete Event Structure

```typescript
interface FunctionEvent {
  payload: Record<string, any>;
  context: {
    snap_in_id: string;
    service_account_id: string;
    secrets: {
      service_account_token: string;
    };
    dev_oid: string;
  };
  execution_metadata: {
    request_id: string;
    devrev_endpoint: string;
    function_name: string;
    event_type: string;
  };
  input_data: {
    global_values: Record<string, any>;
    keyrings: Record<string, string>;
    event_sources: Record<string, string>;
    resources: {
      keyrings: Record<string, KeyringValue>;
    };
  };
}

interface KeyringValue {
  secret: string;
}
```

### Accessing Event Data

```typescript
async function handleEvent(event: FunctionEvent): Promise<void> {
  // Authentication
  const token = event.context.secrets.service_account_token;
  const endpoint = event.execution_metadata.devrev_endpoint;

  // Event info
  const eventType = event.execution_metadata.event_type;
  const functionName = event.execution_metadata.function_name;

  // Configuration inputs
  const config = event.input_data.global_values;
  const greeting = config.greeting_message as string;
  const enabled = config.enabled as boolean;

  // Keyrings (secrets)
  const apiKey = event.input_data.keyrings.api_token;

  // Event payload
  const payload = event.payload;
}
```

## SDK Integration

### Setup Pattern

```typescript
import { client, betaSDK } from "@devrev/typescript-sdk";

async function handleEvent(event: FunctionEvent): Promise<void> {
  const token = event.context.secrets.service_account_token;
  const endpoint = event.execution_metadata.devrev_endpoint;

  // Standard SDK
  const devrevSDK = client.setup({
    endpoint: endpoint,
    token: token,
  });

  // Beta SDK (for newer APIs)
  const devrevBetaSDK = client.setupBeta({
    endpoint: endpoint,
    token: token,
  });

  // Use SDK methods
  const work = await devrevSDK.worksGet({ id: "don:..." });
}
```

### Common SDK Operations

```typescript
// Get work item
const work = await devrevSDK.worksGet({ id: workId });

// Update work item
await devrevSDK.worksUpdate({
  id: workId,
  stage: { name: "resolved" },
});

// Create timeline entry (comment)
await devrevSDK.timelineEntriesCreate({
  object: workId,
  body: "Automated comment",
  type: "timeline_comment",
});

// List work items
const works = await devrevSDK.worksList({
  type: ["ticket"],
  limit: 50,
});
```

## Event Payload Patterns

### work_created / work_updated

```typescript
interface WorkCreatedPayload {
  work_created: {
    work: {
      id: string;
      type: "ticket" | "issue" | "task";
      title: string;
      stage?: { name: string };
      owned_by?: Array<{ id: string }>;
      applies_to_part?: { id: string };
      // ... other fields
    };
  };
}

// Access pattern
const work = event.payload.work_created?.work;
const workId = work?.id;
const workType = work?.type;
```

### conversation_created

```typescript
interface ConversationCreatedPayload {
  conversation_created: {
    conversation: {
      id: string;
      title?: string;
      members?: Array<{ id: string }>;
    };
  };
}

const conversation = event.payload.conversation_created?.conversation;
```

### Timer Events

```typescript
// Timer events have minimal payload
// Use execution_metadata to identify the trigger
const eventType = event.execution_metadata.event_type;
// custom:timer_tick or similar
```

### Custom Webhook Events

```typescript
// External webhook payloads are in event.payload
// Structure depends on external system
const externalData = event.payload;
```

## Function Factory Pattern

### Registration

```typescript
// code/src/function-factory.ts
import on_work_creation from './functions/on_work_creation';
import on_conversation from './functions/on_conversation';
import on_activate from './functions/on_activate';

export const functionFactory = {
  on_work_creation,
  on_conversation,
  on_activate,
} as const;

export type FunctionFactoryType = keyof typeof functionFactory;
```

### Export Index

```typescript
// code/src/index.ts
export { functionFactory } from './function-factory';
```

## Hook Function Patterns

### Activate Hook

```typescript
// code/src/functions/on_activate/index.ts
export const run = async (events: FunctionEvent[]): Promise<void> => {
  const event = events[0];
  const token = event.context.secrets.service_account_token;
  const endpoint = event.execution_metadata.devrev_endpoint;

  const devrevSDK = client.setup({ endpoint, token });

  // Initialization tasks:
  // - Create custom schemas
  // - Validate configuration
  // - Set up initial state

  console.log('Snap-in activated successfully');
};
```

### Deactivate Hook

```typescript
// code/src/functions/on_deactivate/index.ts
export const run = async (events: FunctionEvent[]): Promise<void> => {
  const event = events[0];

  // Cleanup tasks:
  // - Remove temporary resources
  // - Clear state

  console.log('Snap-in deactivated');
};
```

## Command Handler Pattern

```typescript
// code/src/functions/handle_command/index.ts
export const run = async (events: FunctionEvent[]): Promise<void> => {
  for (const event of events) {
    const { payload } = event;

    // Command context
    const objectId = payload.source_id;  // Object where command was invoked
    const userId = payload.actor_id;     // User who invoked

    // Process command
    // ...

    // Optionally respond
    await devrevSDK.timelineEntriesCreate({
      object: objectId,
      body: "Command executed successfully",
      type: "timeline_comment",
    });
  }
};
```

## Async Event Scheduling

Schedule events for later processing:

```typescript
const SCHEDULER_ENDPOINT = '/internal/event-sources.schedule';

async function scheduleEvent(
  eventSourceId: string,
  payload: any,
  delayMs: number,
  token: string,
  endpoint: string
): Promise<void> {
  const body = {
    event_key: `event_${Date.now()}`,
    event_type: 'custom:scheduled_event',
    id: eventSourceId,
    payload: Buffer.from(JSON.stringify(payload)).toString('base64'),
    publish_at: new Date(Date.now() + delayMs).toISOString(),
  };

  await axios.post(
    `${endpoint}${SCHEDULER_ENDPOINT}`,
    body,
    { headers: { Authorization: token } }
  );
}
```

## Best Practices

### Do

- Use TypeScript with proper typing
- Extract service account token from `event.context.secrets`
- Use `@devrev/typescript-sdk` for API calls
- Log meaningful information for debugging
- Handle errors with try-catch
- Process events in a loop

### Avoid

- Hardcoding API tokens or secrets
- Excessive use of `any` type
- Logging service account tokens
- Synchronous blocking operations
- Missing error handling

---

For manifest configuration patterns, see `manifest-schema.md`. For event source setup, see `event-sources.md`.
