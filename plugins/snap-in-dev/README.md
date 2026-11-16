# snap-in-dev

A Claude Code plugin for DevRev Snap-in development. Provides tools for creating and verifying snap-in projects.

## Features

### Commands

#### `/snap-in-dev:new-snap-in [project-name]`

Creates a new DevRev Snap-in project using the DevRev CLI (`devrev snap_in_version init`).

The command:
1. Guides you through an interactive setup asking about project name, description, snap-in type, and events
2. Scaffolds the project using `devrev snap_in_version init` (official DevRev template)
3. Customizes the manifest and code based on your requirements
4. Installs dependencies and verifies the build
5. Runs the snap-in-verifier agent to validate the setup

**Prerequisite**: DevRev CLI must be installed (`npm install -g @devrev/cli`)

### Agents

#### `snap-in-verifier`

Validates snap-in projects for:
- Manifest correctness (version, structure, references)
- Project structure (required files and directories)
- Function implementations (exports, SDK usage)
- Build configuration (TypeScript, dependencies)
- Best practices (error handling, security)

Triggered automatically after `new-snap-in` or manually when you ask to verify a snap-in project.

### Hooks

#### Auto-Verification Hook

The plugin includes a PostToolUse hook that automatically detects when you modify key snap-in files:
- `manifest.yaml`
- `code/src/functions/*/index.ts`
- `code/src/function-factory.ts`
- `code/package.json` (with @devrev/typescript-sdk)

When a snap-in file is modified, you'll receive a suggestion to run the `snap-in-verifier` agent to validate your changes.

## Installation

### Option 1: Local Plugin Directory

```bash
# Copy to your project's plugin directory
cp -r snap-in-dev /path/to/your/project/.claude-plugins/
```

### Option 2: Global Plugin

```bash
# Add to Claude Code with --plugin-dir flag
claude-code --plugin-dir /path/to/snap-in-dev
```

## Usage

### Creating a New Snap-in

```
/snap-in-dev:new-snap-in my-automation
```

Follow the interactive prompts to configure your snap-in.

### Verifying a Snap-in Project

Navigate to your snap-in project directory and ask:

```
Verify my snap-in project
```

Or:

```
Check if my snap-in is configured correctly
```

## Generated Project Structure

```
my-snap-in/
├── manifest.yaml           # Snap-in configuration
├── README.md              # Project documentation
└── code/
    ├── package.json       # Node.js dependencies
    ├── tsconfig.json      # TypeScript config
    ├── .eslintrc.js       # ESLint config
    ├── jest.config.js     # Jest config
    ├── babel.config.js    # Babel config
    └── src/
        ├── index.ts                    # Main exports
        ├── main.ts                     # CLI entry for local testing
        ├── function-factory.ts         # Function registry
        ├── functions/
        │   └── my_function/
        │       └── index.ts            # Function implementation
        └── fixtures/
            └── event.json              # Test fixture
```

## Development Workflow

After creating a snap-in:

1. **Install dependencies**:
   ```bash
   cd my-snap-in/code
   npm install
   ```

2. **Local testing**:
   ```bash
   npm run start -- --functionName=my_function --fixturePath=event.json
   ```

3. **Build**:
   ```bash
   npm run build
   ```

4. **Deploy**:
   ```bash
   devrev profiles authenticate --org <org> --usr <email>
   cd ..  # Back to project root (where manifest.yaml is)
   devrev snap_in_version create-one --path . --create-package
   devrev snap_in draft
   devrev snap_in activate
   ```

## DevRev Documentation

- [Snap-in Concepts](https://developer.devrev.ai/snapin-development/concepts)
- [Manifest Reference](https://developer.devrev.ai/snapin-development/references/v1-manifest)
- [Functions](https://developer.devrev.ai/snapin-development/references/functions)
- [Inputs](https://developer.devrev.ai/snapin-development/references/inputs)
- [Best Practices](https://developer.devrev.ai/snapin-development/best-practices)
- [Local Testing](https://developer.devrev.ai/snapin-development/locally-testing-snap-ins)

## Requirements

- Node.js 18+
- npm or yarn
- DevRev CLI (`npm install -g @devrev/cli`)
- DevRev organization access

## Troubleshooting

### Build Errors

If you encounter TypeScript errors:
1. Ensure `@devrev/typescript-sdk` is installed
2. Check that tsconfig.json has correct settings
3. Run `npm run lint:fix` to auto-fix common issues

### Deployment Errors

If deployment fails:
1. Verify manifest.yaml syntax (use YAML linter)
2. Ensure all functions in manifest have implementations
3. Check that function names match between manifest and code
4. Verify DevRev CLI is authenticated

### Function Not Triggering

If your function doesn't trigger:
1. Check event source configuration in manifest
2. Verify automation connects correct source to function
3. Check event_types match expected DevRev events
4. Review snap-in logs in DevRev console
