# CLAUDE.md

This file provides guidance to Claude Code when working with the Agent Skills Marketplace repository.

## Repository Overview

This is a **plugin marketplace** for Claude Code. Each plugin is a self-contained package with commands, agents, skills, hooks, and scripts.

**Structure:**
```
/plugins/
  /dashboard-dev/     # DevRev dashboard widget creation
  /devrev-mcp/        # DevRev MCP integration
  /snap-in-dev/       # Snap-in development toolkit
```

Each plugin has its own CLAUDE.md with plugin-specific guidance.

## Plugin Development

Use the `plugin-dev` plugin for creating/updating components.

**Plugin structure:**
- `.claude-plugin/plugin.json` - Plugin manifest (name, version, components)
- `commands/` - Slash commands (`.md` files with YAML frontmatter)
- `agents/` - Sub-agents (`.md` files with system prompts)
- `skills/` - Reusable skills (SKILL.md + references/ + examples/)
- `scripts/` - Executable logic (Python, Bash)
- `hooks/` - Event hooks (hooks.json + scripts/)

## Git Workflow

**Branches:**
- `main` - Production-ready plugins
- `feature/*` - New features or plugin updates

**CI/CD:**
- `.github/claude.yml` - Standard CI checks
- `.github/claude-code-review.yml` - Automated PR reviews

**Creating PRs:**
```bash
# Make changes on feature branch
git checkout -b feature/my-plugin-update

# Commit and push
git add .
git commit -m "feat: Description of change"
git push -u origin feature/my-plugin-update

# Create PR to main
gh pr create --base main
```

## Common Tasks

**Test a plugin locally:**
1. Make changes to plugin files
2. Claude auto-discovers from current directory
3. Test commands: `/plugin-name:command-name`

**Add a new plugin:**
1. Create `/plugins/new-plugin-name/` directory
2. Add `.claude-plugin/plugin.json` manifest
3. Add plugin README.md
4. Optionally add CLAUDE.md for plugin-specific guidance
5. Use `/plugin-dev:create-plugin` for guided setup

**Update plugin version:**
- Edit `.claude-plugin/plugin.json` - bump version field
- Follow semantic versioning (major.minor.patch)

## Key Files

- `/plugins/*/CLAUDE.md` - Plugin-specific guidance
- `/.github/` - CI/CD workflows
- `/.gitignore` - Excludes `.env`, local overrides
