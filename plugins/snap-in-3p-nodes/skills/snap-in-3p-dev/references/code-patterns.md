# Code Patterns for 3P Node Operations

Complete code patterns for implementing DevRev snap-in 3P node operations.

## Operation Class Pattern

### Core Template

```typescript
import { betaSDK, client } from '@devrev/typescript-sdk';
import {
  Error as OperationError,
  Error_Type,
  ExecuteOperationInput,
  FunctionInput,
  OperationBase,
  OperationContext,
  OperationOutput,
} from '@devrev/typescript-sdk/dist/snap-ins';
import { handleError } from './helper';

interface MyOperationInput {
  input_field: string;
  optional_field?: number;
  entity_id?: string;      // For entity operations
  items?: string[];        // For array operations
}
interface MyOperationOutput {
  status: boolean;
}
export class MyOperation extends OperationBase {
  constructor(e: FunctionInput) {
    super(e);
  }

  async run(
    context: OperationContext,
    input: ExecuteOperationInput,
    resources: betaSDK.SnapInsResourcesResponse
  ): Promise<OperationOutput> {
    try {
      const input_data = input.data as MyOperationInput;

      // Validate required inputs
      if (!input_data.input_field) {
        return OperationOutput.fromJSON({
          error: {
            message: 'Missing required field: input_field',
            type: Error_Type.InvalidRequest,
          },
        });
      }

      // Get DevRev client (always use this pattern)
      const devrevBetaClient = client.setupBeta({
        endpoint: context.devrev_endpoint,
        token: context.secrets.access_token,
      });

      // Operation logic here
      const result: = await this.processOperation(input_data, devrevBetaClient);

      const outputValue: MyOperationOutput = {
        status: result,
      };

      return OperationOutput.fromJSON({
        output: {
          values: [outputValue],
        } as OutputValue,
        summary: 'My operation completed successfully',
      });
    } catch (error) {
      handleError('MyOperation', error);
      return OperationOutput.fromJSON({
        error: {
          message: error instanceof Error ? error.message : 'Unknown error',
          type: Error_Type.Unknown,
        },
      });
    }
  }

  private async processOperation(input: MyOperationInput, client: any): Promise<string> {
    // Implement operation logic
    return true;
  }
}
```

### Variations

**Entity ID Operation:**
```typescript
// Validate entity_id
if (!input_data.entity_id) {
  return OperationOutput.fromJSON({
    error: { message: 'Missing entity_id', type: Error_Type.InvalidRequest },
  });
}

// Use entity_id with DevRev APIs
const entity = await devrevBetaClient.worksGet({ id: input_data.entity_id });
```

**Array Operation:**
```typescript
// Validate array
const items = input_data.items || [];
if (items.length === 0) {
  return OperationOutput.fromJSON({
    error: { message: 'Items array cannot be empty', type: Error_Type.InvalidRequest },
  });
}

// Process array
const results = await Promise.all(items.map(item => this.processItem(item)));
```

---

## Helper Utilities

**File:** `code/src/functions/operation_handler/helper.ts`

```typescript
import { client } from '@devrev/typescript-sdk';
import { Error_Type, OperationOutput } from '@devrev/typescript-sdk/dist/snap-ins';

export function getClient(endpoint: string, token: string) {
  return client.setupBeta({ endpoint, token });
}

export function buildError(message: string, type: Error_Type = Error_Type.Unknown): OperationOutput {
  return OperationOutput.fromJSON({
    error: { message, type },
  });
}

/** Log error with context; use in catch before returning OperationOutput. Do not log tokens or full responses. */
export function handleError(context: string, error: unknown): void {
  if (error instanceof Error) {
    console.error(`${context} - Error: ${error.message}`);
  } else {
    console.error(`${context} - Unknown Error:`, error);
  }
}

/** Returns OperationOutput for catch block; logs via handleError when context is useful. */
export function errorToOutput(error: unknown): OperationOutput {
  const message = error instanceof Error ? error.message : 'Unknown error';
  return buildError(message);
}
```

**Usage in operation run():**
```typescript
import { getClient, handleError, errorToOutput } from './helper';

// ... in run()
try {
  // operation logic
} catch (error) {
  handleError('MyOperation', error);  // consistent logging with context
  return errorToOutput(error);
}
```

---

## Operation Handler Index

**File:** `code/src/functions/operation_handler/index.ts`

```typescript
import { ExecuteOperationInput, FunctionInput, OperationMap } from '@devrev/typescript-sdk/dist/snap-ins';
import { OperationFactory } from '../../operations';
import { Operation1 } from './operation-1';
import { Operation2 } from './operation-2';

const operationMap: OperationMap = {
  operation_1: Operation1,
  operation_2: Operation2,
};

export const run = async (events: FunctionInput[]) => {
  const event = events[0];
  const payload = event.payload as ExecuteOperationInput;
  const operationSlug = payload.metadata!.slug;
  
  const operationFactory = new OperationFactory(operationMap);
  const operation = operationFactory.getOperation(operationSlug, event);
  const ctx = operation.GetContext(event);
  const resources = event.input_data.resources || {};
  
  return await operation.run(ctx, payload, resources);
};

export default run; // CRITICAL: Must export default
```

---

## OperationFactory Class

**File:** `code/src/operations/index.ts` (Created by `devrev init`, rarely modify)

```typescript
import { FunctionInput, OperationIfc, OperationMap } from '@devrev/typescript-sdk/dist/snap-ins';

export class OperationFactory {
  operationMap: OperationMap;

  constructor(operationMap?: OperationMap) {
    this.operationMap = operationMap || {};
  }

  public getOperation(slug: string, event: FunctionInput): OperationIfc {
    if (!this.operationMap[slug]) {
      throw new Error(`Operation with slug ${slug} not found`);
    }
    return new this.operationMap[slug](event);
  }
}
```

---

## Function Factory

**File:** `code/src/function-factory.ts`

```typescript
import operation_handler from './functions/operation_handler'; // CRITICAL: default import

export const functionFactory = {
  operation_handler,
} as const;

export type FunctionFactoryType = keyof typeof functionFactory;
```

**Rules:** Must use default import, never `import * as operation_handler`

---

## Main Index Entry Point

**File:** `code/src/index.ts` (Usually no modifications needed)

```typescript
import { FunctionExecutionRequest } from '@devrev/typescript-sdk/dist/snap-ins';
import { functionFactory, FunctionFactoryType } from './function-factory';

export const run = async (events: FunctionExecutionRequest[]) => {
  for (const event of events) {
    const functionType = event.execution_metadata.function_name as FunctionFactoryType;
    if (!(functionType in functionFactory)) {
      console.error(`Function type ${functionType} not found`);
      continue;
    }
    await functionFactory[functionType](event.payload.function_inputs);
  }
};

export default run;
```

---

## Manifest Examples

### Basic Operation

```yaml
operations:
  - name: my_operation
    display_name: My Operation
    description: Operation description
    slug: my_operation
    function: operation_handler
    type: action
    inputs:
      fields:
        - name: input_field
          field_type: text
          description: Input description
          is_required: true
          ui:
            display_name: Input Field
    outputs:
      fields:
        - name: result
          field_type: text
          description: Result description
          is_required: true
          ui:
            display_name: Result
```

### Entity ID Input

```yaml
inputs:
  fields:
    - name: entity_id
      field_type: id
      id_type: [ticket, issue, contact]
      description: Entity ID
      is_required: true
      ui:
        display_name: Entity ID
```

### Array Input

```yaml
inputs:
  fields:
    - name: items
      field_type: array
      base_type: text
      description: List of items
      is_required: true
      ui:
        display_name: Items
```

### Enum Array (List Picker)

```yaml
inputs:
  fields:
    - name: enum_picker
      field_type: array
      base_type: enum
      allowed_values: [value-1, value-2, value-3]
      default_value: [value-1]
      is_required: true
      ui:
        display_name: Enum Picker
```

### Composite Types

```yaml
inputs:
  fields:
    - name: items
      field_type: array
      base_type: composite
      composite_type: item
      is_required: true
  composites:
    - name: item
      fields:
        - name: name
          field_type: text
          is_required: true
        - name: properties
          field_type: text
          is_required: true
```

---

## Critical Patterns

### File Structure
```
code/src/
├── index.ts                    # Main entry
├── function-factory.ts         # Function registry
├── operations/index.ts         # OperationFactory
└── functions/operation_handler/
    ├── index.ts                # Operation map (export default run)
    ├── helper.ts               # Utilities (optional)
    └── my-operation.ts         # Operation classes
```

### Export Rules
1. `operation_handler/index.ts` → `export default run`
2. `function-factory.ts` → `import operation_handler from` (default import)
3. Operation classes → extend `OperationBase`, implement `run()`
4. All returns → `OperationOutput.fromJSON()`

### Input Validation
```typescript
if (!required_field) {
  return OperationOutput.fromJSON({
    error: { message: 'Missing required field', type: Error_Type.InvalidRequest },
  });
}
```

### Array Safety
```typescript
const items = input_data.items || [];
if (items.length === 0) {
  // Handle empty array
}
```

### DevRev Client
```typescript
const devrevBetaClient = client.setupBeta({
  endpoint: context.devrev_endpoint,
  token: context.secrets.access_token,
});
// Never use context.devrev directly
```

### Error Handling
```typescript
try {
  // Operation logic
} catch (error) {
  console.error('Operation failed', error);
  return OperationOutput.fromJSON({
    error: {
      message: error instanceof Error ? error.message : 'Unknown error',
      type: Error_Type.Unknown,
    },
  });
}
```

---

## Quick Reference

| Component | Location | Key Rule |
|-----------|----------|----------|
| Operation Class | `functions/operation_handler/my-operation.ts` | Extend `OperationBase`, implement `run()` |
| Operation Map | `functions/operation_handler/index.ts` | Map slug→class, `export default run` |
| OperationFactory | `operations/index.ts` | Auto-created, rarely modify |
| Function Factory | `function-factory.ts` | Default import for operation_handler |
| Helper Utilities | `functions/operation_handler/helper.ts` | Optional reusable functions |
| Manifest | Root `manifest.yaml` | Define operations with inputs/outputs |

---

## Common Mistakes & Best Practices

### Wrong Export Pattern
```typescript
// Wrong - operation_handler/index.ts
export const run = async (events) => { ... };
// Missing default export!

// Correct
export const run = async (events) => { ... };
export default run;

// Wrong - function-factory.ts
import * as operation_handler from './functions/operation_handler';

// Correct
import operation_handler from './functions/operation_handler';
```

### Unsafe Array Access
```typescript
// Wrong
const firstItem = input_data.items[0]; // Crashes if empty

// Correct
const items = input_data.items || [];
if (items.length === 0) {
  return OperationOutput.fromJSON({
    error: { message: 'Items cannot be empty', type: Error_Type.InvalidRequest }
  });
}
const firstItem = items[0];
```

### Setup Workflow
```bash
# 1. Initialize
cd snap-in/
devrev snap_in_version init <name>

# 2. Install dependencies (critical - do this first!)
cd <name>/code
npm install

# 3. Clean up (init creates on_work_creation etc.; 3P nodes need only operation_handler)
rm -rf src/functions/on_work_creation
# or remove all event-handler folders: rm -rf src/functions/on_*

# 4. Edit manifest.yaml, create operation class, register in map
```

### Quick Troubleshooting

| Problem | Solution |
|---------|----------|
| "Cannot find module '@devrev/typescript-sdk'" | Run `npm install` in `code/` |
| Operation not found | Check slug matches in manifest and operation map |
| Default export error | Ensure `export default run` and default import |
| Array access crash | Check `array.length` before accessing |

## Additional Resources

- **Manifest Schema:** `manifest-schema.md` - Complete manifest and field type reference
- **API Reference:** `api-reference.md` - Complete API reference with SDK types and operations
