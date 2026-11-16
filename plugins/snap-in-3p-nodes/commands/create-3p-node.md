---
name: create-3p-node
description: Interactive workflow to create a complete DevRev snap-in 3P node operation from requirements to implementation
allowed-tools: [Read, Write, Edit, Bash, Task, AskUserQuestion, Glob, Grep]
---

# Create 3P Node Command

This command guides you through creating a complete DevRev snap-in 3P node operation using an intelligent, interactive workflow.

## What This Command Does

Creates a production-ready 3P node operation by:
1. **Gathering requirements** - Understanding what the operation should do
2. **Analyzing solutions** - Determining if DevRev APIs can solve it or if external integration is needed
3. **Researching** - Investigating external APIs, NPM packages, and auth patterns (if needed)
4. **Generating code** - Creating manifest.yaml and TypeScript operation handler
5. **Validating** - Ensuring code quality, security, and correctness

## How to Use

Simply run the command and answer the interactive questions:

```
/create-3p-node
```

The command will spawn the `3p-workflow-agent` which will guide you through the entire process step-by-step.

## Workflow Overview

### Step 1: Requirements Gathering
The agent will ask:
- What should this operation do?
- What inputs does it need?
- What outputs should it produce?
- Any specific requirements or constraints?

### Step 2: Solution Analysis
The agent analyzes whether:
- **DevRev APIs** can handle it (works, parts, accounts, etc.)
- **External APIs** are needed (third-party services like Slack, SendGrid, etc.)

### Step 3: Research (if external APIs needed)
If external integration is required, the agent will:
- Ask your permission to spawn a research agent
- Research official API documentation
- Find appropriate NPM packages
- Document authentication patterns
- Provide implementation recommendations

### Step 3.5: Initialize snap-in (new snap-in only)
When creating a **new** snap-in (no existing project at the target path), the workflow will:
- Run `devrev snap_in_version init <snap-in-name>` from the snap-in parent directory
- Remove the `on_work_creation` folder (3P nodes use only `operation_handler`)
- Run `npm install` in the code directory
- Then generate only manifest, operation handler, and registration into this initialized structure (it does not create the project from scratch).

### Step 4: Code Generation
The generator agent creates (in an init-based project):
- **manifest.yaml** - Operation definition with proper field types
- **TypeScript operation class** - Complete implementation with error handling
- **Operation registration** - Proper export patterns and operation map

### Step 5: Validation
The validator agent checks:
- Manifest syntax and field types
- TypeScript code structure and exports
- DevRev API usage (correct methods and entity mapping)
- Security best practices (no token logging, input validation)

## Important Notes

**Always interactive**: This command ignores any arguments and always uses an interactive workflow. This ensures all requirements are properly understood.

**Spawns workflow agent**: The command will spawn the `3p-workflow-agent` to handle the entire process autonomously.

**Complete output**: The generated code is production-ready and includes full error handling, validation, and security best practices.

**References available**: The agent has access to:
- `skills/snap-in-3p-dev/references/manifest-schema.md` - Complete manifest field type reference
- `skills/snap-in-3p-dev/references/api-reference.md` - DevRev API methods and patterns
- `skills/snap-in-3p-dev/references/code-patterns.md` - TypeScript implementation templates
- `scripts/validate-manifest.sh` - Manifest validation utility

## Related Commands

- `/research-api` - Research external API integration only (without full workflow)
- `/validate-3p-node` - Validate existing 3P node implementation

## Example Usage

```
user: /create-3p-node
agent: I'll help you create a 3P node operation. Let me start by understanding what you need.

What should this operation do? What's its purpose?

user: Send an email notification when a ticket is created

agent: Got it! This will require external email service integration. Let me gather more details...
[Interactive workflow continues...]
```

## Tips

- **Be specific**: Clear requirements lead to better code generation
- **Review generated code**: Always review before deploying
- **Use validation**: The validator catches common mistakes
- **Check references**: The skills/snap-in-3p-dev/references/ directory has detailed documentation

---

**Implementation Instructions:**

When this command is executed:

1. Use the Task tool to spawn the workflow agent with subagent_type="snap-in-3p-nodes:3p-workflow-agent"
2. Pass the user's context and working directory information to the agent
3. Let the workflow agent handle the entire interactive process
4. The workflow agent will spawn other agents as needed (research, generator, validator)

**Example spawn:**
```
Task tool with:
  subagent_type: "snap-in-3p-nodes:3p-workflow-agent"
  description: "Create 3P node operation"
  prompt: "Guide the user through creating a 3P node operation. Start by asking what the operation should do, then follow the complete workflow: requirements → analysis → research (if needed) → generation → validation."
```
