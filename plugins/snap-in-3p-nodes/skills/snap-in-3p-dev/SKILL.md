---
name: Snap-in 3P Nodes Development
description: This skill should be used when the user asks to "create a 3P node", "build a third-party node", "add a 3P operation", "configure operation handler", "set up 3P integration", "implement 3P node handler", "fix operation code", "debug 3P node", "review operation code", or mentions DevRev snap-in operations, manifest configuration, operation handlers, or fixing API usage issues in snap-ins.
version: 1.0.0
---

# Snap-in 3P Nodes Development

Guide for creating third-party (3P) nodes in DevRev snap-ins - custom operations invokable from DevRev's UI or API.

### Quick Start with Commands

**Create a complete 3P node:**
```
/create-3p-node
```
Launches an interactive workflow that:
1. **Gathers requirements** - Asks what the operation should do, what inputs/outputs it needs
2. **Analyzes solutions** - Determines if DevRev APIs can handle it or if external integration is needed
3. **Researches external APIs** - If needed, investigates official docs, NPM packages, and auth patterns
4. **Generates complete code** - Creates manifest.yaml and TypeScript operation handler (production-ready)
5. **Validates implementation** - Checks manifest, code, API usage, and security

**Research an external API only:**
```
/research-api
```
Investigates a specific external service (Slack, SendGrid, etc.) and provides:
- Official API documentation links
- Recommended NPM packages
- Authentication patterns
- Code examples for DevRev snap-ins

**Validate existing implementation:**
```
/validate-3p-node
```
Comprehensive validation of manifest and code checking:
- Manifest syntax and field types
- TypeScript structure and exports
- DevRev API correctness (works vs parts)
- Security best practices

### How the Workflow Works

When you run `/create-3p-node`, the plugin spawns specialized agents:

1. **3p-workflow-agent** (orchestrator)
   - Guides you through the entire process interactively
   - Asks clarifying questions about your requirements
   - Coordinates research, generation, and validation

2. **3p-research-agent** (when external APIs needed)
   - Researches official API documentation using web search
   - Finds appropriate NPM packages
   - Documents authentication methods (OAuth, API keys, etc.)
   - Provides DevRev-specific integration guidance

3. **3p-generator-agent** (code creation)
   - Generates complete manifest.yaml with proper field types
   - Creates TypeScript operation class with full error handling
   - Implements input validation and security practices
   - Registers operation in operation map with correct exports

4. **3p-validator-agent** (quality assurance)
   - Validates manifest against schema (no unsupported types)
   - Checks TypeScript exports and structure
   - Verifies correct DevRev API usage (Enhancement is Part, not Work!)
   - Ensures security (no token logging, input validation)

### When to Use Interactive vs Manual

**Use interactive workflow (`/create-3p-node`) when:**
- Creating a new 3P node operation
- Integrating with external APIs (Slack, SendGrid, Stripe, etc.)
- Unsure about DevRev API methods to use
- Want production-ready code with full error handling

**Use manual approach (sections below) when:**
- Making small tweaks to existing operations
- You already know exactly what code to write
- Learning about 3P node internals and patterns
- Debugging specific issues

### Automatic Validation Hooks

This plugin includes **hooks** that automatically validate your changes:

- **PreToolUse hook** - Warns before making invalid manifest changes (unsupported field types, missing id_type, etc.)
- **PostToolUse hook** - Automatically runs `validate-manifest.sh` after modifying manifest.yaml

## Core Components

Every 3P node requires three elements:
1. **Operation definition in manifest.yaml** - Defines inputs, outputs, and metadata
2. **Operation handler class** - Implements the operation logic
3. **Operation map registration** - Maps operation slug to handler class

## Quick Start

Initialize a new snap-in using DevRev CLI:

```bash
cd snap-in/
devrev snap_in_version init <snap-in-name>
cd <snap-in-name>/code
rm -rf src/functions/on_work_creation   # init creates this; 3P nodes need only operation_handler
npm install
```

**Critical:** Run `npm install` immediately after initialization to install SDK types. Delete the `on_work_creation` folder (and any other `on_*` event handler directories) after init—3P nodes only need `operation_handler`.

## File Structure

```
snap-in/snap-in-name/
├── manifest.yaml              # Operation definitions
└── code/
    ├── package.json
    ├── tsconfig.json
    └── src/
        ├── index.ts
        ├── function-factory.ts
        ├── operations/index.ts       # OperationFactory class
        └── functions/operation_handler/
            ├── index.ts              # Operation map and run function
            └── my-operation.ts        # Operation class
```

All files are created by `devrev snap_in_version init`. Modify as needed.

## Creating a 3P Node

Follow this sequence:

1. **Initialize snap-in (if starting from scratch)** - Run `devrev snap_in_version init <snap-in-name>` from your `snap-in/` directory, then `cd <snap-in-name>/code` and `npm install`. This creates the correct folder structure, manifest stub, and SDK types. Skip this step if you already have an existing snap-in project.
2. **Define operation in manifest.yaml** - Specify inputs, outputs, and operation metadata
3. **Create operation class** - Extend `OperationBase` and implement `run()` method
4. **Register in operation map** - Add slug→class mapping in `operation_handler/index.ts`
5. **Verify exports** - Ensure default exports are correct in handler and function factory

**Supported field types:** `id`, `text`, `array`, `bool`, `int`

**See reference files for complete details:**
- `skills/snap-in-3p-dev/references/manifest-schema.md` - Field types, validation rules, common mistakes
- `skills/snap-in-3p-dev/references/code-patterns.md` - Templates, export patterns, setup workflow, troubleshooting
- `skills/snap-in-3p-dev/references/api-reference.md` - API methods, entity mapping, security practices

**Validate manifest:** Run `scripts/validate-manifest.sh` before deployment.

## Critical Reminders

### Field Types
Use only: `id` (with `id_type` array), `text`, `array`, `bool`, `int`. Never use: `enum`, `rich_text`, `object`, `date`.

### Entity-to-API Mapping
- **Works entities** (Ticket/Issue/Opportunity/Task) → Use `works*` APIs
- **Parts entities** (Product/Capability/Feature/**Enhancement**) → Use `parts*` APIs

**CRITICAL:** Enhancement is a Part, NOT a Work! Use `partsCreate()`, not `worksCreate()`.

### DevRev Client Setup
Always use:
```typescript
const devrevBetaClient = client.setupBeta({
  endpoint: context.devrev_endpoint,
  token: context.secrets.access_token,
});
```

Never use `context.devrev` directly.

### Error Handling
All returns must use `OperationOutput.fromJSON()` with appropriate `Error_Type` values.

### Security
Never log tokens, API responses, or sensitive data. Safe to log: operation status, entity IDs, counts.

### Export Pattern
- `operation_handler/index.ts` must `export default run`
- `function-factory.ts` must use `import operation_handler from` (default import)

## Additional Resources

### Validation Script

- **`scripts/validate-manifest.sh`** - Validates manifest.yaml syntax, checks for unsupported field types, verifies required fields, and catches common mistakes

Usage: `./scripts/validate-manifest.sh [path-to-manifest.yaml]`

### Reference Files

Each reference file includes complete details with common mistakes and best practices:

- **`skills/snap-in-3p-dev/references/manifest-schema.md`** - Complete schema, field types, validation rules
- **`skills/snap-in-3p-dev/references/code-patterns.md`** - Templates, export patterns, setup workflow, troubleshooting
- **`skills/snap-in-3p-dev/references/api-reference.md`** - API methods, entity-to-API mapping, security practices

### SDK Types Location

After running `npm install`, access SDK types:
- Operations types: `code/node_modules/@devrev/typescript-sdk/dist/snap-ins/types.d.ts`
- API types: `code/node_modules/@devrev/typescript-sdk/dist/auto-generated/beta/beta-devrev-sdk.d.ts` (~30,000 lines)

**CRITICAL:** Never read the entire `beta-devrev-sdk.d.ts` file. Use `grep` to search for specific types first, then read only the needed sections:

```bash
# Search for specific type
grep -n "WorksCreateRequest" code/node_modules/@devrev/typescript-sdk/dist/auto-generated/beta/beta-devrev-sdk.d.ts

# Then read only that section (e.g., lines 5000-5100)
read_file target_file offset=5000 limit=100
```

### External Resources

- **DevRev API Reference:** https://developer.devrev.ai/api-reference - Always verify API methods before use
