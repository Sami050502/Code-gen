# DevRev API Reference for 3P Nodes

Complete reference for DevRev API operations and SDK types used in 3P nodes.

**Primary resource:** https://developer.devrev.ai/api-reference  
**Always verify API methods from official documentation before use.**

---

## SDK Types Location

**Standard paths (after `npm install`):**
- **Operations:** `code/node_modules/@devrev/typescript-sdk/dist/snap-ins/types.d.ts`
- **Interfaces:** `code/node_modules/@devrev/typescript-sdk/dist/snap-ins/interfaces.d.ts`
- **Full API:** `code/node_modules/@devrev/typescript-sdk/dist/auto-generated/beta/beta-devrev-sdk.d.ts` (~30,000 lines - read specific sections as needed)

**Usage:** Read these files directly using `read_file` tool when you need specific type definitions.

---

## Common Operation Types

```typescript
// From @devrev/typescript-sdk/dist/snap-ins

import {
  Error as OperationError,
  Error_Type,
  ExecuteOperationInput,
  FunctionInput,
  OperationBase,
  OperationContext,
  OperationOutput,
} from '@devrev/typescript-sdk/dist/snap-ins';

// OperationContext
type OperationContext = {
  devrev_endpoint: string;
  secrets: { access_token: string };
  dev_oid: string;
  input_port: string;
};

// OperationBase class - extend for operations
export class OperationBase {
  GetContext(...args: any[]): OperationContext;
}

// OperationOutput - use for all returns
OperationOutput.fromJSON({ output: {...} });  // Success
OperationOutput.fromJSON({ error: {...} });   // Error
```

---

## Client Setup

```typescript
import { betaSDK, client } from '@devrev/typescript-sdk';

function getClient(endpoint: string, token: string) {
  return client.setupBeta({ endpoint, token });
}

const devrevBetaClient = getClient(
  context.devrev_endpoint,
  context.secrets.access_token
);
```

**CRITICAL:** Always use `client.setupBeta()`. Never use `context.devrev` directly.

---

## API Operations

### Works API (`works*`)
**For:** Ticket, Issue, Opportunity, Task  
**Methods:** `worksCreate`, `worksGet`, `worksList`, `worksUpdate`, `worksDelete`  
**Response:** `response.data.work` (single) or `response.data.works` (array)

```typescript
// Create
const ticket = (await devrevBetaClient.worksCreate({
  type: betaSDK.WorkType.Ticket,
  title: "Support Request",
  owned_by: [userId],
})).data.work;

// Get
const work = (await devrevBetaClient.worksGet({ id: workId })).data.work;

// List
const works = (await devrevBetaClient.worksList({
  type: [betaSDK.WorkType.Ticket],
  limit: 50,
})).data.works;

// Update
await devrevBetaClient.worksUpdate({ id: workId, title: "Updated" });

// Delete
await devrevBetaClient.worksDelete({ id: workId });
```

### Parts API (`parts*`)
**For:** Product, Capability, Feature, Enhancement, Linkable, Runnable  
**Methods:** `partsCreate`, `partsGet`, `partsList`, `partsUpdate`, `partsDelete`  
**Response:** `response.data.part` (single) or `response.data.parts` (array)

**CRITICAL:** Enhancement, Feature, Capability, Product are **Parts, NOT Works!**

**Key differences:**
- Parts use `name` (not `title`)
- Parts use `parent_part: [id]` (array, not `applies_to_part`)

```typescript
// Create Enhancement (Part - NOT Work!)
const enhancement = (await devrevBetaClient.partsCreate({
  type: betaSDK.PartType.Enhancement,
  name: "New Feature",  // Use 'name', not 'title'
  parent_part: [productId],  // Array required
  owned_by: [userId],
})).data.part;

// Get, List, Update, Delete follow same pattern
const part = (await devrevBetaClient.partsGet({ id: partId })).data.part;
const parts = (await devrevBetaClient.partsList({
  type: [betaSDK.PartType.Enhancement],
  limit: 50,
})).data.parts;
```

### Other APIs

- **Accounts:** `accountsCreate`, `accountsGet`, `accountsList`, `accountsUpdate`, `accountsDelete`, `accountsMerge`, `accountsExport`
- **DevUsers:** `devUsersCreate`, `devUsersGet`, `devUsersList`, `devUsersUpdate`, `devUsersActivate`, `devUsersDeactivate`, `devUsersMerge`, `devUsersSelf`, `devUsersSelfUpdate`
- **RevUsers:** `revUsersCreate`, `revUsersGet`, `revUsersList`, `revUsersUpdate`, `revUsersDelete`, `revUsersMerge`, `revUsersScan`
- **RevOrgs:** `revOrgsCreate`, `revOrgsGet`, `revOrgsList`, `revOrgsUpdate`, `revOrgsDelete`
- **Groups:** `groupsCreate`, `groupsGet`, `groupsList`, `groupsUpdate`
- **GroupMembers:** `groupMembersAdd`, `groupMembersRemove`, `groupMembersList`
- **ServiceAccounts:** `serviceAccountsCreate`, `serviceAccountsGet`, `serviceAccountsUpdate`
- **Articles:** `createArticle`, `getArticle`, `listArticles`, `updateArticle`, `deleteArticle`, `articlesCount`  
  **Response:** `response.data.article` (single) or `response.data.articles` (array)
- **Artifacts:** `artifactsGet`, `artifactsList`, `artifactsLocate`, `artifactsPrepare`, `artifactsVersionsPrepare`, `artifactsHardDeleteVersion`  
  **Note:** Use `artifactsPrepare` to create and get upload URL, then upload file

---

## Entity-to-API Mapping

| Entity Type | Base Type | Create API | Type Enum | Response Field |
|------------|-----------|------------|-----------|----------------|
| **Ticket** | Work | `worksCreate` | `WorkType.Ticket` | `data.work` / `data.works` |
| **Issue** | Work | `worksCreate` | `WorkType.Issue` | `data.work` / `data.works` |
| **Opportunity** | Work | `worksCreate` | `WorkType.Opportunity` | `data.work` / `data.works` |
| **Task** | Work | `worksCreate` | `WorkType.Task` | `data.work` / `data.works` |
| **Product** | Part | `partsCreate` | `PartType.Product` | `data.part` / `data.parts` |
| **Capability** | Part | `partsCreate` | `PartType.Capability` | `data.part` / `data.parts` |
| **Feature** | Part | `partsCreate` | `PartType.Feature` | `data.part` / `data.parts` |
| **Enhancement** | Part | `partsCreate` | `PartType.Enhancement` | `data.part` / `data.parts` |
| **Account** | Org | `accountsCreate` | - | `data.account` / `data.accounts` |
| **RevOrg** | Org | `revOrgsCreate` | - | `data.rev_org` / `data.rev_orgs` |
| **DevUser** | User | `devUsersCreate` | - | `data.dev_user` / `data.dev_users` |
| **RevUser/Contact** | User | `revUsersCreate` | - | `data.rev_user` / `data.rev_users` |
| **Group** | Atom | `groupsCreate` | - | `data.group` / `data.groups` |
| **ServiceAccount** | User | `serviceAccountsCreate` | - | `data.service_account` |
| **Article** | Atom | `createArticle` | - | `data.article` / `data.articles` |
| **Artifact** | Atom | `artifactsPrepare` | - | `data.artifact` / `data.artifacts` |

### Field Naming Differences

| Field | Works (Ticket/Issue) | Parts (Product/Feature) |
|-------|---------------------|------------------------|
| Name/Title | `title` | `name` |
| Parent | `applies_to_part` (single) | `parent_part` (array) |
| Type enum | `WorkType` | `PartType` |

---

## Request/Response Types

**Common patterns:**
- `[Entity]CreateRequest` / `[Entity]CreateResponse`
- `[Entity]UpdateRequest` / `[Entity]UpdateResponse`
- `[Entity]GetRequest` / `[Entity]GetResponse`
- `[Entity]ListRequest` / `[Entity]ListResponse`
- `[Entity]DeleteRequest` / `[Entity]DeleteResponse`

**Examples:**
- `WorksCreateRequest`, `WorksCreateResponse`
- `PartsCreateRequest`, `PartsCreateResponse`
- `AccountsCreateRequest`, `AccountsCreateResponse`

**Access types:** Read from `node_modules/@devrev/typescript-sdk/dist/auto-generated/beta/beta-devrev-sdk.d.ts` after `npm install`.

---

## Best Practices

### Verify API Methods Before Use

1. Check https://developer.devrev.ai/api-reference for method names and parameters
2. Review existing snap-ins for real-world examples (see snap-in-dev skill)
3. Search TypeScript SDK types in `node_modules/@devrev/typescript-sdk/dist/` after `npm install`
4. Verify response structure

### Response Structure Safety

**Always verify response structure:**
```typescript
// Verify single response
if (!response.data?.work) {
  throw new Error('Work not found');
}
const work = response.data.work;

// Verify array response
const works = response.data.works || [];
if (works.length === 0) {
  // Handle empty case
}
```

### Entity-to-API Mapping Rules

- **Works** (Ticket, Issue, Opportunity, Task) → Use `works*` APIs
- **Parts** (Product, Capability, Feature, Enhancement) → Use `parts*` APIs
- **Parts use:** `name` (not `title`), `parent_part: [id]` (array, not `applies_to_part`)

---

## Verification Checklist

Before using any API method:

1. Check https://developer.devrev.ai/api-reference
2. Verify method name and parameters
3. Check response structure (`data.work` vs `data.works`)
4. Handle edge cases (empty arrays, missing fields)
5. Use correct API for entity type (Works vs Parts)

---

## Critical: SDK File Reading

**NEVER read the entire `beta-devrev-sdk.d.ts` file (~30,000 lines).**

**Token usage estimate:** Reading the entire file would consume ~30,000-50,000+ tokens, which is wasteful and unnecessary.

**Instead:**
- Use `grep` to search for specific types/methods first
- Read only the specific sections you need (e.g., `WorksCreateRequest`, `PartsCreateResponse`)
- Use the official API reference: https://developer.devrev.ai/api-reference
- Check this document's examples and patterns first

**Example safe approach:**
```bash
# Search for specific type
grep -n "WorksCreateRequest" code/node_modules/@devrev/typescript-sdk/dist/auto-generated/beta/beta-devrev-sdk.d.ts

# Then read only that section (e.g., lines 5000-5100)
read_file target_file offset=5000 limit=100
```

---

## Entity-to-API Mapping

**Works entities** → Use `works*` APIs:
- Ticket, Issue, Opportunity, Task

**Parts entities** → Use `parts*` APIs:
- Product, Capability, Feature, **Enhancement**

**CRITICAL:** Enhancement is a Part, NOT a Work!

```typescript
// Wrong - Enhancement is not a Work
await client.worksCreate({ type: 'enhancement', ... });

// Correct - Enhancement is a Part
await client.partsCreate({ type: 'enhancement', ... });
```

---

## Security Best Practices

**NEVER log:**
- `context.secrets.access_token`
- API keys or credentials
- Full API responses (may contain PII)
- Sensitive user data

**Safe to log:**
```typescript
console.log('Operation started:', operationSlug);
console.log('Processing entity:', entityId);
console.log('Items count:', items.length);
```

**Error logging:** Use a context-aware handler so errors are logged without exposing tokens or full responses (see `code-patterns.md` Helper Utilities):
```typescript
function handleError(context: string, error: unknown): void {
  if (error instanceof Error) {
    console.error(`${context} - Error: ${error.message}`);
  } else {
    console.error(`${context} - Unknown Error:`, error);
  }
}
// In catch: handleError('MyOperation', error); then return OperationOutput.fromJSON({ error: {...} });
```

**DevRev Client Setup:**
```typescript
// Always use this pattern
const client = client.setupBeta({
  endpoint: context.devrev_endpoint,
  token: context.secrets.access_token,
});

// Never use context.devrev directly (deprecated)
```
