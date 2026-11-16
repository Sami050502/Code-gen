---
name: review-plugin
description: Review plugin components using plugin-dev agents and skills
argument-hint: "[type: skill|agent|command|hook|all] [name]"
allowed-tools: Task, Read, Bash, Grep, Glob, AskUserQuestion, Skill
---

Review plugin components using plugin-dev validators. This is a development helper command.

## Arguments

- `$1` - Component type: `skill`, `agent`, `command`, `hook`, or `all`
- `$2` - (Optional) Specific component name to review

## Step 1: Parse Arguments

If `$1` is provided, use it as the type. If `$2` is provided, use it as the specific component name.

If no arguments provided, ask:

```
AskUserQuestion:
  question: "What component type to review?"
  header: "Target"
  options:
    - "all" - "Full plugin validation"
    - "skill" - "Review skills"
    - "agent" - "Review agents"
    - "command" - "Review commands"
    - "hook" - "Review hooks"
  multiSelect: false
```

## Step 2: Find Components

Based on type and optional name:

### Type: all
Run full plugin validation.

### Type: skill
- If name provided: Find `skills/$2/SKILL.md`
- If no name: List all skills in `skills/*/SKILL.md` and ask which to review

### Type: agent
- If name provided: Find `agents/$2.md`
- If no name: List all agents in `agents/*.md` and ask which to review

### Type: command
- If name provided: Find `commands/$2.md`
- If no name: List all commands in `commands/*.md` and ask which to review

### Type: hook
Review `hooks/hooks.json`

## Step 3: Run Review

Route to appropriate plugin-dev agent or skill:

| Type | Has Agent? | Use |
|------|-----------|-----|
| all | Yes | `plugin-dev:plugin-validator` agent |
| skill | Yes | `plugin-dev:skill-reviewer` agent |
| agent | Yes | `plugin-dev:agent-creator` agent (review mode) |
| command | No | Load `/plugin-dev:command-development` skill and review against guidelines |
| hook | No | Load `/plugin-dev:hook-development` skill and review against guidelines |

### For types with dedicated agents (all, skill, agent):

```
Task: plugin-dev:<agent-name>
Prompt: |
  Review the following plugin component:

  Type: [type]
  Path: [file_path]

  Provide a detailed review with:
  - Critical issues (must fix)
  - Important issues (should fix)
  - Suggestions (nice to have)
```

### For types without dedicated agents (command, hook):

1. Load the corresponding skill using `Skill` tool
2. Read the component file
3. Review against the skill's guidelines and patterns
4. Generate review report with same severity categories

## Step 4: Report Results

Format output as:

```
## Review: [component_name]

### Critical Issues
- Issue 1 (file:line if applicable)

### Important Issues
- Issue 1

### Suggestions
- Suggestion 1

### Summary
[X] critical, [Y] important, [Z] suggestions
```

## Examples

```bash
# Review all plugin components
/review-plugin all

# Review a specific skill
/review-plugin skill widget-development

# Review a specific agent
/review-plugin agent widget-generator

# Review all commands
/review-plugin command

# Review a specific command
/review-plugin command create-dashboard

# Review hooks
/review-plugin hook
```
