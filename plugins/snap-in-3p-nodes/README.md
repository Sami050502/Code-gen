# Snap-in 3P Nodes Plugin

Claude Code plugin for creating DevRev snap-in 3P node operations with an interactive workflow: requirements → analysis → research (if needed) → code generation → validation.

## Install

```bash
cc --plugin-dir /path/to/snap-in-3p-nodes
```

## Commands

| Command | Purpose |
|--------|---------|
| `/create-3p-node` | Full workflow: gather requirements, analyze solution, research APIs if needed, generate manifest + TypeScript, validate |
| `/research-api` | Research an external API (docs, NPM packages, auth) without generating code |
| `/validate-3p-node` | Validate existing 3P node (manifest, TypeScript, API usage, security) |

## Quick start

1. Run `/create-3p-node`.
2. Answer the questions (what the operation should do, inputs, outputs).
3. The workflow will generate manifest.yaml and operation code, then validate.

You can also say “create a 3P node” or “build a 3P operation” in chat to start the same workflow.

## What’s included

- **Agents:** 3p-workflow (orchestrator), 3p-research, 3p-generator, 3p-validator
- **References:** `skills/snap-in-3p-dev/references/manifest-schema.md`, `skills/snap-in-3p-dev/references/api-reference.md`, `skills/snap-in-3p-dev/references/code-patterns.md`
- **Hooks:** PreToolUse/PostToolUse on manifest edits to catch mistakes early
- **Script:** `scripts/validate-manifest.sh` for manifest validation

## Links

- [DevRev API Reference](https://developer.devrev.ai/api-reference)
- [DevRev Snap-ins](https://developer.devrev.ai/snap-ins)
