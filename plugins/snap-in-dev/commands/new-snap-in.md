---
description: Interactively create and setup a DevRev Snap-in using AskUserQuestion to collect requirements
argument-hint: [description]
allowed-tools: AskUserQuestion, Read, Write, Bash, Task, TodoWrite, Grep
---

# DevRev Snap-in Creation Workflow

Guide the user through creating a complete DevRev snap-in project interactively.

**Initial description (if provided):** $ARGUMENTS - If provided, infer the snap-in project name from this description.

---

## AskUserQuestion Rules

1. **One question per invocation** - Never batch multiple questions
2. **Wait for response** before proceeding to the next question
3. **Prefer multiple choice** - Generate dynamic options based on context. Users can always select "Other" for custom input
4. **Store answers** for use in subsequent steps

---

## Step 1: Check for Existing Settings

Check if `.claude/snap-in-dev.local.md` exists (may have been created by `/plan-snap-in`).

**If file exists:**
1. Read the file and parse YAML frontmatter
2. Extract: project_name, snap_in_type, event_type, description, external_system, auth_method, api_docs_url
3. Display: "Found existing configuration from planning session"
4. **INVOKE AskUserQuestion:**

```json
{
  "questions": [
    {
      "question": "Use the saved configuration from your planning session?",
      "header": "Config",
      "multiSelect": false,
      "options": [
        {
          "label": "Yes, use saved",
          "description": "Initialize with previously planned settings"
        },
        {
          "label": "No, start fresh",
          "description": "Ignore saved settings and configure manually"
        }
      ]
    }
  ]
}
```

- **"Yes, use saved"**: Skip to Step 5 (Initialize Project) using saved values
- **"No, start fresh"**: Proceed to Step 3 as normal

**If file does not exist:** Proceed to Step 3.

---

## Step 2: Create Todo List

Create a todo list:

1. Gather project requirements (mark as in_progress)
2. Initialize project with DevRev CLI
3. Configure external system integration
4. Generate plugin settings
5. Install dependencies
6. Initialize Git repository
7. Validate project setup

---

## Step 3: Gather Project Requirements

### 3a. Snap-in Type

If $ARGUMENTS is provided, use it as description and infer a kebab-case project name.

**INVOKE AskUserQuestion:**

```json
{
  "questions": [
    {
      "question": "What type of snap-in are you building?",
      "header": "Type",
      "multiSelect": false,
      "options": [
        {
          "label": "Event-triggered",
          "description": "Responds to DevRev events like work_created, ticket_updated"
        },
        {
          "label": "Timer-based",
          "description": "Runs on a schedule with cron expressions"
        },
        {
          "label": "External webhook",
          "description": "Receives events from external systems"
        },
        {
          "label": "Command/Button",
          "description": "Adds custom commands or buttons to DevRev UI"
        }
      ]
    }
  ]
}
```

Store the selected type for Step 3b and Step 5.

### 3b. Type-Specific Configuration

**If "Event-triggered":** INVOKE AskUserQuestion:

```json
{
  "questions": [
    {
      "question": "Which DevRev event should trigger your snap-in?",
      "header": "Event",
      "multiSelect": false,
      "options": [
        {
          "label": "work_created",
          "description": "When any work item is created"
        },
        {
          "label": "work_updated",
          "description": "When any work item is updated"
        },
        {
          "label": "conversation_created",
          "description": "When a conversation starts"
        },
        {
          "label": "ticket_created/updated",
          "description": "When tickets are created or updated"
        }
      ]
    }
  ]
}
```

**If "Timer-based":** Ask for cron expression (e.g., '0 9 \* \* \*' for daily at 9am).

**If "External webhook":** Ask about external system name and expected event structure.

**If "Command/Button":** Ask about command name and where it should appear in DevRev UI.

### 3c. Description

If $ARGUMENTS was not provided, ask for a brief description (1-2 sentences).

---

## Step 4: External System Integration

**INVOKE AskUserQuestion:**

```json
{
  "questions": [
    {
      "question": "Does this snap-in require integration with external systems?",
      "header": "Integration",
      "multiSelect": false,
      "options": [
        {
          "label": "Yes",
          "description": "I need to integrate with an external system"
        },
        { "label": "No", "description": "This snap-in only uses DevRev APIs" }
      ]
    }
  ]
}
```

### 4a. If External Integration Needed

**INVOKE AskUserQuestion** for system:

```json
{
  "questions": [
    {
      "question": "Which external system will you integrate with?",
      "header": "System",
      "multiSelect": false,
      "options": [
        { "label": "GitHub", "description": "GitHub API integration" },
        { "label": "Jira", "description": "Jira/Atlassian integration" },
        { "label": "Slack", "description": "Slack API integration" },
        { "label": "Custom API", "description": "Other REST/GraphQL API" }
      ]
    }
  ]
}
```

**INVOKE AskUserQuestion** for auth method:

```json
{
  "questions": [
    {
      "question": "What authentication method does the external system use?",
      "header": "Auth",
      "multiSelect": false,
      "options": [
        { "label": "API Key", "description": "Simple API key authentication" },
        { "label": "OAuth 2.0", "description": "OAuth credentials flow" },
        {
          "label": "Bearer Token",
          "description": "Bearer token authentication"
        },
        {
          "label": "Basic Auth",
          "description": "Username/password authentication"
        }
      ]
    }
  ]
}
```

Then ask for API documentation URL.

### 4b. Summary Confirmation

Show configuration summary:

```
Project Configuration Summary:
- Name: [project name]
- Type: [snap-in type]
- Event: [event type, if applicable]
- Description: [description]
- External Integration: [Yes/No]
  [If Yes: System, Auth, API Docs]
```

**INVOKE AskUserQuestion:**

```json
{
  "questions": [
    {
      "question": "Does this configuration look correct?",
      "header": "Confirm",
      "multiSelect": false,
      "options": [
        {
          "label": "Yes, proceed",
          "description": "Continue with project setup"
        },
        {
          "label": "No, start over",
          "description": "Re-enter configuration from the beginning"
        }
      ]
    }
  ]
}
```

- **"Yes, proceed"**: Mark todo complete, proceed to Step 5
- **"No, start over"**: Return to Step 3a
- **"Other"**: Ask what to modify, return to relevant section

**DO NOT PROCEED TO STEP 5** until user selects "Yes, proceed".

---

## Step 5: Initialize and Configure Project

Mark "Initialize project with DevRev CLI" as in_progress.

1. Run `devrev snap_in_version init [project_name]`
2. Update manifest.yaml with description and snap-in type
3. Configure event sources based on type
4. If external integration needed, add keyring configuration

Mark as completed.

---

## Step 6: Generate Plugin Settings File

Mark "Generate plugin settings" as in_progress.

Create `.claude/snap-in-dev.local.md` with project configuration. Ensure it's added to .gitignore.

Mark as completed.

---

## Step 7: Install Dependencies

Mark "Install dependencies" as in_progress.

Install base dependencies. If external integration needed:

1. Install appropriate SDK (e.g., @octokit/rest, @slack/web-api, axios)
2. Add example integration code showing keyring access
3. Verify build completes

Mark as completed.

---

## Step 8: Initialize Git Repository

Mark "Initialize Git repository" as in_progress.

Initialize git repo. Ensure .gitignore includes node_modules, build outputs, .env, .claude/\*.local.md. Create initial commit.

Mark as completed.

---

## Step 9: Validation

Mark "Validate project setup" as in_progress.

Launch snap-in-verifier agent to validate project structure, manifest, and code. Address any critical errors.

Mark as completed.

---

## Step 10: Getting Started

Provide next steps:

**Local Testing:**

```bash
cd [project_name]/code
npm run start -- --functionName=[function-name] --fixturePath=fixtures/[event]_event.json
```

**Deployment:**

```bash
cd [project_name]
devrev snap_in_version create-one --path . --create-package
devrev snap_in draft
devrev snap_in activate
```

---

## Command Complete

Summary:

- **Project**: [project_name]
- **Type**: [snapin_type]
- **Event**: [event_type if applicable]
- **External Integration**: [Yes/No with details]
- **Git Repository**: Initialized
- **Dependencies**: Installed
- **Settings File**: Created
- **Validation**: Completed

**Location**: ./[project_name]/

---

## Security Notes

- Never hardcode API keys - use keyrings
- .env and .claude/\*.local.md are gitignored
- Use HTTPS for external API calls
- Validate external data
