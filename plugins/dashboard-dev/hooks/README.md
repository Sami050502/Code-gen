# Dashboard Dev Plugin Hooks

This directory contains Claude Code hooks that automate validation and configuration for dashboard development.

## Hooks Overview

### SessionStart Hook: Configuration Validator

**Script**: `scripts/check-workspace-config.sh`

**Purpose**: Validates environment setup and auto-generates `config.yaml` on session start.

**Behavior**:

1. **Check if config.yaml exists**
   - If present: Hook exits silently ✓
   - If missing: Proceed to validation

2. **Check CLI availability**
   - If `dashboard-sync` not installed: Hook exits silently
   - Required for config generation

3. **Validate .env file**
   - **Missing .env**: Show prominent warning with setup steps
   - **Incomplete .env**: Show warning about missing variables
   - **Valid .env**: Proceed to config generation

4. **Auto-generate config.yaml**
   - Calls: `dashboard-sync config init`
   - Fetches organization metadata from DevRev API
   - Creates `config.yaml` with org ID, name, prefix, endpoints
   - Shows success message on completion

**Exit Behavior**: Always exits with code 0 (non-blocking)

#### Example Outputs

**Scenario 1: Missing .env**
```
⚠️  Environment not configured

   Missing: .env file

   Setup steps:
   1. cp .env.example .env
   2. Add your DEVREV_PAT and DEVREV_ENDPOINT
   3. Restart Claude Code session
```

**Scenario 2: Incomplete .env**
```
⚠️  Environment not configured

   .env exists but missing required variables:
   - DEVREV_PAT
   - DEVREV_ENDPOINT

   Add these to .env and restart session
```

**Scenario 3: Auto-generation Success**
```
🔧 Auto-generating config.yaml...

✓ config.yaml generated
  Org: Maple

✓ Workspace configuration created successfully
```

**Scenario 4: config.yaml Already Exists**
*(Silent - no output)*

### PostToolUse Hooks: Widget & Dashboard Validation

**Scripts**:
- `scripts/validate-widget-generation.sh`
- `scripts/validate-dashboard-generation.sh`

**Trigger**: After `Write` or `Edit` tool use

**Purpose**: Automatically validate generated widget and dashboard JSON files

**Behavior**:
- Detects widget/dashboard JSON files in Write/Edit operations
- Runs 3-stage validation pipeline:
  1. **Structure**: JSON schema validation
  2. **Semantic**: Business rules (SQL, viz types, field types)
  3. **API**: Platform dry-run validation
- Logs errors to `logs/validation-errors.jsonl`
- Returns feedback to agent for correction (max 3 attempts)

## Hook Configuration

Hooks are registered in `hooks.json`:

```json
{
  "hooks": {
    "SessionStart": [
      {
        "hooks": [{
          "type": "command",
          "command": "bash ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/check-workspace-config.sh",
          "timeout": 30
        }]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": "bash ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/validate-widget-generation.sh",
            "timeout": 30
          },
          {
            "type": "command",
            "command": "bash ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/validate-dashboard-generation.sh",
            "timeout": 30
          }
        ]
      }
    ]
  }
}
```

## Development

### Testing Hooks Locally

```bash
# Test SessionStart hook
cd your-workspace
bash /path/to/plugin/hooks/scripts/check-workspace-config.sh

# Test with different scenarios
rm .env                    # Test missing .env
echo "SOME_VAR=x" > .env  # Test incomplete .env
cp .env.example .env      # Test complete .env
```

### Adding New Hooks

1. Create script in `hooks/scripts/`
2. Make executable: `chmod +x script-name.sh`
3. Register in `hooks.json`
4. Test in workspace
5. Document in this README

## Troubleshooting

### Hook Not Running

**Check plugin is active:**
```bash
# Verify plugin directory structure
ls -la .claude/plugins/dashboard-dev/hooks/
```

**Check hook execution:**
- Hooks log to stderr/stdout (visible in Claude Code)
- Check `logs/validation-errors.jsonl` for validation hooks

### Config Generation Fails

**Common causes:**
- Invalid credentials in .env
- API endpoint unreachable
- CLI not installed (`pipx install dashboard-sync`)

**Manual fix:**
```bash
dashboard-sync init
```

### Hook Timeout

- Default timeout: 30 seconds
- Increase in `hooks.json` if needed for slow networks
- API calls may be rate-limited

## Best Practices

1. **Non-blocking**: Hooks should never block Claude Code sessions
2. **Informative**: Provide clear error messages with actionable steps
3. **Idempotent**: Safe to run multiple times without side effects
4. **Fast**: Complete within timeout (30s default)
5. **Logged**: Write validation results to `logs/` directory

## Related Documentation

- [Plugin ARCHITECTURE.md](../ARCHITECTURE.md) - Overall plugin design
- [Widget Development Skill](../skills/widget-development/SKILL.md) - Widget creation guidance
- [Validation Pipeline](../scripts/widget/README.md) - Validation rule details
