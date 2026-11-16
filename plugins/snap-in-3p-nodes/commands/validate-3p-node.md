---
name: validate-3p-node
description: Comprehensive validation of DevRev snap-in 3P node implementation including manifest, TypeScript code, API usage, and security best practices
allowed-tools: [Task, Read, Bash, Glob, Grep]
---

# Validate 3P Node Command

Perform comprehensive validation of an existing DevRev snap-in 3P node implementation to catch errors, security issues, and best practice violations before deployment.

## What This Command Does

Validates all aspects of a 3P node implementation:
- **Manifest validation** - Syntax, field types, required properties
- **TypeScript code** - Structure, exports, type safety
- **DevRev API usage** - Correct methods, entity-to-API mapping
- **Security practices** - Token logging, credential exposure, input validation

## When to Use This

Run this validation:
- **Before deployment** - Catch issues early
- **After manual code changes** - Verify correctness
- **When troubleshooting** - Identify problems systematically
- **During code review** - Ensure quality standards

## How to Use

Run the command from within your snap-in directory:

```
/validate-3p-node
```

The command will:
1. Detect your snap-in structure automatically
2. Spawn the validator agent
3. Perform comprehensive checks
4. Provide a detailed validation report

## What Gets Validated

### 1. Manifest (manifest.yaml)

**Checks:**
- YAML syntax correctness
- Required fields present (name, display_name, description, slug, etc.)
- Field types are supported (id, text, array, bool, int only)
- ID fields have required `id_type` array
- Array fields have required `base_type`
- Enum arrays have `allowed_values`
- Composite arrays reference defined composites
- Snake_case naming convention
- No unsupported types (enum, rich_text, object, date)

**Uses:** `scripts/validate-manifest.sh`

### 2. TypeScript Code Structure

**Checks:**
- Operation classes extend `OperationBase`
- Operation classes implement `run()` method
- Correct imports from SDK
- operation_handler/index.ts exports `default run`
- function-factory.ts uses default import
- Operation map has slug→class mappings
- All operations in manifest are in operation map
- Type safety (proper interfaces defined)

### 3. DevRev API Usage

**Checks:**
- Client setup uses `client.setupBeta()` (not `context.devrev`)
- Works entities use `works*` APIs (Ticket, Issue, Opportunity, Task)
- Parts entities use `parts*` APIs (Product, Capability, Feature, Enhancement)
- Enhancement uses `partsCreate()` NOT `worksCreate()`
- Parts use `name` field (not `title`)
- Parts use `parent_part` array (not `applies_to_part`)
- Correct response field access (`.data.work` vs `.data.works`)
- Proper type enums (`WorkType`, `PartType`)

### 4. Security Best Practices

**Checks:**
- No token logging (`context.secrets.access_token`)
- No logging of full API responses
- No hardcoded credentials
- Input validation for required fields
- Safe array access (check length before accessing)
- Error handling in try-catch blocks
- Proper error types in `OperationOutput.fromJSON()`

### 5. Code Patterns

**Checks:**
- All returns use `OperationOutput.fromJSON()`
- Proper error handling with appropriate `Error_Type`
- Input validation for required fields
- Safe access patterns for optional fields
- Consistent code style

## Validation Report Format

The validator provides a structured report with severity levels:

### Errors (Must Fix)
Critical issues that will cause failures:
```
ERROR: Unsupported field type 'enum' in manifest.yaml
   Location: operations.inputs.fields[2].field_type
   Fix: Use field_type: array with base_type: enum instead
```

### Warnings (Should Fix)
Issues that may cause problems:
```
WARNING: Enhancement entity using worksCreate()
   Location: functions/operation_handler/create-enhancement.ts:42
   Fix: Enhancement is a Part, use partsCreate() instead
```

### Info (Best Practices)
Recommendations for improvement:
```
INFO: Consider adding input validation
   Location: functions/operation_handler/send-email.ts:28
   Suggestion: Validate email format before making API call
```

### Success
```
All validations passed! Your 3P node is ready for deployment.

Summary:
- Manifest: Valid
- TypeScript: Valid
- API Usage: Correct
- Security: Secure
- Total issues: 0 errors, 0 warnings, 2 info suggestions
```

## Example Usage

```
user: /validate-3p-node

agent: I'll validate your 3P node implementation. Let me check your snap-in...
[Spawns validator agent]

agent: Validation complete! Found 2 errors and 1 warning:

ERROR: Missing id_type for field 'entity_id'
   Location: manifest.yaml:15
   Fix: Add id_type: [ticket, issue] to the field definition

ERROR: Using worksCreate() for Enhancement
   Location: code/src/functions/operation_handler/create-item.ts:45
   Fix: Use partsCreate() - Enhancement is a Part, not a Work

WARNING: Logging full API response
   Location: code/src/functions/operation_handler/get-data.ts:33
   Fix: Remove console.log of response (may contain PII)

INFO: Consider validating array before access
   Location: code/src/functions/operation_handler/process-items.ts:28

Summary: 2 errors, 1 warning, 1 info
Status: Must fix errors before deployment
```

## Validation Scope

The validator checks files in these locations:
- `manifest.yaml` (root)
- `code/src/functions/operation_handler/` (all TypeScript files)
- `code/src/operations/index.ts`
- `code/src/function-factory.ts`
- `code/src/index.ts`

## Related Commands

- `/create-3p-node` - Create new 3P node with built-in validation
- `/research-api` - Research external API integration patterns

## Tips

- **Run before deployment**: Always validate before deploying
- **Fix errors first**: Address critical errors before warnings
- **Use auto-validation**: Hooks automatically validate manifest changes
- **Check references**: See `skills/snap-in-3p-dev/references/` for detailed documentation
- **Incremental validation**: Run after each significant change

## Automatic Validation

This plugin includes hooks that automatically validate:
- **PreToolUse hook**: Warns before making invalid manifest changes
- **PostToolUse hook**: Runs validation after manifest.yaml modifications

Manual validation with this command provides more comprehensive checks.

---

**Implementation Instructions:**

When this command is executed:

1. Detect the snap-in directory structure (look for manifest.yaml and code/src/)
2. Use the Task tool to spawn the validator agent with subagent_type="snap-in-3p-nodes:3p-validator-agent"
3. Pass the working directory and file paths to the agent
4. Display the formatted validation report with severity indicators

**Example spawn:**
```
Task tool with:
  subagent_type: "snap-in-3p-nodes:3p-validator-agent"
  description: "Validate 3P node implementation"
  prompt: "Validate the 3P node implementation in the current directory. Check manifest.yaml, TypeScript code, DevRev API usage, and security practices. Provide a detailed report with errors, warnings, and suggestions."
```
