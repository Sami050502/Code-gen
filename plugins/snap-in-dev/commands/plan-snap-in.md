---
description: Discover snap-in requirements interactively and generate a development plan using Plan and Explorer agents
argument-hint: [snap-in name or description]
allowed-tools: AskUserQuestion, Read, Write, Bash, Task, TodoWrite, Grep, Glob
---

# Snap-in Development Planning

Help users discover requirements for their snap-in and produce a detailed development plan.

**Initial input (if provided):** $ARGUMENTS

---

## AskUserQuestion Rules

1. **Batch questions** - Ask multiple, multi-choice questions in a single invocation when possible
2. **Wait for response** before proceeding to the next question
3. **Prefer multiple choice** - Generate dynamic options based on context. Users can always select "Other" for custom input
4. **Store answers** for use in subsequent steps

---

## Step 1: Select Project Context

**INVOKE AskUserQuestion:**

```json
{
  "questions": [
    {
      "question": "What is the goal of this session?",
      "header": "Goal",
      "multiSelect": false,
      "options": [
        {
          "label": "Create new snap-in",
          "description": "Start a fresh project"
        },
        {
          "label": "Work on existing",
          "description": "Fix bug, add feature, or enhance an existing snap-in"
        }
      ]
    }
  ]
}
```

### 1a. New Snap-in

If "Create new snap-in":

1. **INVOKE AskUserQuestion:**
   ```json
   {
     "questions": [
       {
         "question": "What should the new snap-in be called?",
         "header": "Project Name",
         "multiSelect": false,
         "options": [
           {
             "label": "Enter name",
             "description": "Provide a name (kebab-case recommended)"
           }
         ]
       }
     ]
   }
   ```
2. Store `project_name`.
3. Proceed to **Step 2: Gather Requirements**.

### 1b. Existing Snap-in

If "Work on existing":

1. Use `Glob` to list directories in `.plans/` to identify available projects (look for `.plans/*/snap-in-config.md`).
2. **INVOKE AskUserQuestion**:
   - Present found projects as options.
   - Ask user to select the target project.
3. Read the selected project's `.plans/{project_name}/snap-in-config.md`.
4. Parse frontmatter to load existing configuration (`snap_in_type`, `event_types`, `core_functionality`, etc.).
5. **INVOKE AskUserQuestion**:
   ```json
   {
     "questions": [
       {
         "question": "What updates would you like to make?",
         "header": "Task",
         "multiSelect": false,
         "options": [
           { "label": "Fix a bug" },
           { "label": "Add a feature" },
           { "label": "Enhance existing functionality" }
         ]
       }
     ]
   }
   ```
6. Proceed to **Step 2**, using loaded context to skip or pre-fill inquiries.

---

## Step 2: Gather Requirements

**Note for Existing Projects:** If working on an existing snap-in (selected in Step 1b), check the loaded configuration for values before asking user questions. Use `AskUserQuestion` to confirm changes or fill missing details.

Create a todo list:

1. Gather business requirements (mark as in_progress)
2. Gather technical & manifest requirements
3. Explore similar snap-ins
4. Generate development plan
5. Save settings

### 2a. Project Name

If `project_name` was collected in Step 1, skip this step.

If $ARGUMENTS is provided and `project_name` is not set, infer a kebab-case project name from it.

Otherwise, **INVOKE AskUserQuestion:**

```json
{
  "questions": [
    {
      "question": "What should this snap-in be called?",
      "header": "Name",
      "multiSelect": false,
      "options": [
        {
          "label": "Describe it",
          "description": "I'll describe what it does and you suggest a name"
        }
      ]
    }
  ]
}
```

If user selects "Other" or "Describe it", ask them to describe the snap-in and infer an appropriate kebab-case name.

### 2b. Business & User Experience

**INVOKE AskUserQuestion:**

```json
{
  "questions": [
    {
      "question": "What is the primary goal and user experience?",
      "header": "Goal",
      "multiSelect": false,
      "options": [
        {
          "label": "Describe functionality",
          "description": "Explain what the snap-in does for the user"
        }
      ]
    },
    {
      "question": "Who is the intended audience?",
      "header": "Target",
      "multiSelect": false,
      "options": [
        { "label": "Admins", "description": "Configures system behavior" },
        { "label": "Support Agents", "description": "Works on tickets" },
        { "label": "Developers", "description": "Works on issues" },
        { "label": "All Users", "description": "General utility" }
      ]
    }
  ]
}
```

Store `core_functionality` and `audience`.

### 2c. Snap-in Type

**INVOKE AskUserQuestion:**

```json
{
  "questions": [
    {
      "question": "What type of snap-in is this?",
      "header": "Type",
      "multiSelect": false,
      "options": [
        {
          "label": "Event-Driven Automations",
          "description": "React to DevRev platform events"
        },
        {
          "label": "Command-Based",
          "description": "Triggered by user slash commands"
        },
        {
          "label": "Timer-Based",
          "description": "Scheduled via cron expressions"
        },
        {
          "label": "External Webhooks",
          "description": "Receive events from external systems"
        },
        {
          "label": "Operations",
          "description": "Reusable actions with defined I/O"
        },
        {
          "label": "Hook-Based",
          "description": "Validate snap-in lifecycle events"
        },
        {
          "label": "Interactive UI",
          "description": "Snap Kit actions for UI elements"
        }
      ]
    }
  ]
}
```

Store `snap_in_type`.

### 2d. Technical & Manifest Requirements

Based on the selected type, gather specific technical details.

1. **Event Sources & Triggers:**
   Ask about specific events (e.g., `work_created`, `ticket_updated`), cron schedules, or webhook signatures.
   _Suggest configuration based on type (e.g. `devrev-webhook` for Event-Driven, `timer-events` for Timer-Based)._

2. **Input Fields (Configuration):**
   **INVOKE AskUserQuestion:**

   ```json
   {
     "questions": [
       {
         "question": "What configuration fields do users need?",
         "header": "Inputs",
         "multiSelect": true,
         "options": [
           { "label": "API Key/Token", "description": "Secure text field" },
           { "label": "Notification Channel", "description": "String or ID" },
           { "label": "Sync Strategy", "description": "Enum choice" },
           { "label": "Object ID", "description": "DevRev reference" },
           {
             "label": "Boolean Toggle",
             "description": "Enable/Disable feature"
           }
         ]
       },
       {
         "question": "What is the configuration scope?",
         "header": "Scope",
         "multiSelect": false,
         "options": [
           {
             "label": "Organization-level",
             "description": "Shared across all users"
           },
           { "label": "User-level", "description": "Per-user configuration" }
         ]
       }
     ]
   }
   ```

3. **DevRev Entities:**
   Ask which DevRev objects (Work, Parts, Tickets, RevUsers) the snap-in will read or write.

### 2e. External Integrations

**INVOKE AskUserQuestion:**

```json
{
  "questions": [
    {
      "question": "Does this snap-in integrate with external systems?",
      "header": "Integration",
      "multiSelect": false,
      "options": [
        { "label": "Yes", "description": "Calls external APIs" },
        { "label": "No", "description": "DevRev only" }
      ]
    }
  ]
}
```

If **Yes**: Ask for System Name, Auth Method, and API Docs URL.

### 2f. Final Confirmation

Present a summary of collected requirements to the user.

**INVOKE AskUserQuestion:**

```json
{
  "questions": [
    {
      "question": "Ready to generate the plan?",
      "header": "Confirm",
      "multiSelect": false,
      "options": [
        { "label": "Generate Plan", "description": "Proceed to planning" },
        {
          "label": "Modify Requirements",
          "description": "Go back and changes details"
        }
      ]
    }
  ]
}
```

```json
{
  "questions": [
    {
      "question": "What is the main thing this snap-in should do?",
      "header": "Function",
      "multiSelect": false,
      "options": [
        {
          "label": "Sync data",
          "description": "Keep DevRev in sync with external systems"
        },
        {
          "label": "Automate workflow",
          "description": "Automate tasks based on events"
        },
        {
          "label": "Send notifications",
          "description": "Notify external systems of DevRev events"
        },
        {
          "label": "Enrich data",
          "description": "Add information to DevRev objects"
        }
      ]
    }
  ]
}
```

Store the core functionality.

---

## Step 3: Explore Similar Snap-ins

Mark "Explore similar snap-ins" as in_progress.

Launch the **snap-in-explorer** agent with collected requirements:

- **Snap-in type**: [snap_in_type from Step 2c]
- **Event types**: [event_types if applicable]
- **Features needed**: keyrings (if external integration), automation, etc.
- **Core functionality**: [from Step 2b]

The agent will:
1. Search the snap-in index for matching examples
2. Analyze manifest.yaml and function files from 2-3 relevant snap-ins
3. Return structured findings with absolute file paths, line numbers, and summaries

Store the agent's findings for use in Step 4.

Mark as completed.

---

## Step 4: Generate Development Plan

Mark "Generate development plan" as in_progress.

Use the Plan agent to create a detailed implementation plan.

**Planning prompt:**

```
Generate a development plan for a DevRev snap-in.

## User Brief
Name: [project_name]
Description: [description]

## Product Requirements
- Type: [snap_in_type]
- Trigger: [event_type or trigger]
- Core Functionality: [core_functionality]

## Technical Requirements
- External Integration: [external_system]
- Auth Method: [auth_method]
- API Docs: [api_docs_url]

## Relevant Additional Context
[Include findings from Step 3 with absolute paths, excerpts, and summaries]

## Development Plan Content
The plan must only include:
1. **Manifest Configuration**: Essential parts of `manifest.yaml` (event sources, functions, automations).
2. **Core Function Implementation**: High-signal pseudo-code or logic for the main handler.
3. **Key Patterns Discovered**: Specific implementations found in similar snap-ins (do NOT include SDK initialization).
4. **Similar Snap-ins Referenced**: List of relevant examples (name and what they do).
5. **Best Practices**: Add these specific practices at the bottom of the plan:
   1. Use JQ filters to reduce unnecessary function invocations
   2. Extract configuration at function entry
   3. Process events sequentially with await
   4. Validate inputs early (use hooks for deployment-time validation)
   5. Verify external webhook signatures with Rego policies
   6. Provide fixtures for local testing
   7. Separate common utilities into shared modules

## Constraints
- **Exclusions**: Do NOT include project initialization, directory creation, local testing setup, deployment steps, or DevRev testing instructions.
- **Style**: Use short, minimal sentences or bullet-point instructions. Focus on non-obvious, high-signal steps. Avoid standard boilerplate.
- **Patterns**: Explicitly exclude SDK initialization details.
```

Present the generated plan to the user.

**INVOKE AskUserQuestion:**

```json
{
  "questions": [
    {
      "question": "Does this development plan look good?",
      "header": "Plan",
      "multiSelect": false,
      "options": [
        {
          "label": "Yes, save it",
          "description": "Save settings and plan to proceed"
        },
        {
          "label": "Modify plan",
          "description": "I want to adjust some aspects"
        },
        {
          "label": "Start over",
          "description": "Requirements need to change"
        }
      ]
    }
  ]
}
```

- **"Yes, save it"**: Proceed to Step 5
- **"Modify plan"**: Ask what to change, regenerate relevant sections
- **"Start over"**: Return to Step 2

Mark as completed.

---

## Step 5: Save Settings and Plan

Mark "Save configuration and plan" as in_progress.

1. **Snap-in Configuration**:
   Create or update `.plans/[project_name]/snap-in-config.md` with:

   ```markdown
   ---
   project_name: [kebab-case-name]
   snap_in_type:
     [
       Event-Driven Automations|Command-Based|Timer-Based|External Webhooks|Operations|Hook-Based|Interactive UI,
     ]
   event_types: [list of events]
   description: [brief description]
   external_systems: [list of systems]
   auth_method: [method]
   core_functionality: [functionality]
   plan_files:
     - .plans/[project_name]/[project_name].initial_plan.md
   ---
   ```

2. **Development Plan**:
   Save the generated plan to `.plans/[project_name]/[project_name].initial_plan.md`.

3. **Global Settings** (checking existence only):
   Ensure `.claude/snap-in-dev.local.md` contains necessary paths if used later (e.g., `snap-in-examples_repo_path`, `devrev_objects_path`, `manifest_index_path`, `archetype_repo_path`, `flow_repo_path`). Do not overwrite if it exists.

Mark as completed.

---

## Command Complete

Summary:

- **Project**: [project_name]
- **Type**: [snap_in_type]
- **Trigger**: [event_type or trigger mechanism]
- **External Integration**: [Yes/No with details]
- **Core Functionality**: [functionality]
- **Settings File**: `.plans/[project_name]/snap-in-config.md`
- **Development Plan**: Generated and saved to `.plans/[project_name]/[project_name].initial_plan.md`

**Next steps:**

1. Review the development plan in `.plans/[project_name]/[project_name].initial_plan.md`
2. Run `/new-snap-in .plans/[project_name]/[project_name].initial_plan.md` to initialize the project
3. Follow the specific non-obvious steps outlined in the plan

---

## Tips

- Re-run this command anytime to update requirements or regenerate the plan
- The settings file persists your configuration for future sessions
- Use `/new-snap-in` after planning to scaffold the project
- The Explorer agent finds real patterns from existing snap-ins
- The Plan agent creates actionable implementation steps
