# Agent Skills Marketplace

This repository is a distributable marketplace for **Agent Skills** built on the open Agent Skills standard.

It hosts production-ready, versioned plugins composed of commands, agents, skills, hooks, and executable scripts that AI agents can dynamically load to enable reliable, repeatable automation.

Each plugin is self-contained and owns its own documentation, architecture, and usage guidance.

---

## Repository Structure

```
/plugins
  /dashboard-dev
    README.md        # Plugin overview and usage
    ARCHITECTURE.md # Architecture and orchestration
    commands/        # Slash commands
    agents/          # Sub-agents
    skills/          # Reusable Agent Skills
    scripts/         # Executable logic and validation
```

## Quick Start

### 1. Install the Plugin

1. Run `/plugins` to open the plugin manager
2. Go to **Marketplaces** tab
3. Click **+ Add Marketplace**
4. Enter: `git@github.com/devrev/aai-skills.git`
5. Browse to **dashboard-dev** and click **Install**

### 2. Initialize Your Workspace

Navigate to your project directory and create a `.env` file with your DevRev credentials:

```
DEVREV_PAT=your_personal_access_token
DEVREV_ENDPOINT=https://api.devrev.ai
```

**Note:** Both `DEVREV_PAT` and `DEVREV_ENDPOINT` are required. Get your PAT from DevRev Settings → API Tokens.

### 3. Create Your First Dashboard

Just tell Claude what you want to see:

```
Create a dashboard that displays issues, grouped by account, and filtered by sprint.
```

Claude will:
1. Generate a plan with appropriate widgets
2. Query the schema for available fields
3. Generate widget JSON files with proper SQL
4. Validate and save to `dashboards/`
5. Assemble the complete dashboard

## Example Dashboards

Try these example prompts to get started:

### 1. Support Team Dashboard
```
Create a dashboard for support teams with:
- Tickets by state (table)
- Ticket trends over time (line chart)
- Top priority issues (table)
```

### 2. Customer Success Dashboard
```
Create a dashboard showing:
- Conversations by channel (donut chart)
- Account engagement metrics (table)
- Response time trends (line chart)
```

### 3. Product Analytics Dashboard
```
Create a dashboard with:
- Issues by priority (bar chart)
- Feature requests by state (table)
- Bug trends over last 30 days (line chart)
```

### 4. Sales Dashboard
```
Create a dashboard displaying:
- Opportunities by state (donut chart)
- Account tier distribution (table)
- Revenue metrics (metric cards)
```

## Documentation
- [Agent Skills](https://agentskills.io/)
- [Claude Code Docs](https://code.claude.com/)
- [Skills Guide](https://code.claude.com/docs/en/skills)
- [Plugin Discovery](https://code.claude.com/docs/en/discover-plugins)
- [Plugin Marketplaces](https://code.claude.com/docs/en/plugin-marketplaces)
