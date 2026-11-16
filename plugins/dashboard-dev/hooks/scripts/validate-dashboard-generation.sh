#!/bin/bash
# Dashboard validation hook for PostToolUse
# Validates dashboards/*.json files after Write or Edit

set -e

# Read input from stdin (hook receives JSON context)
input=$(cat)
FILE=$(echo "$input" | jq -r '.tool_input.file_path // empty')

# Check if this is a dashboard file
# CRITICAL: Only match dashboard.json files, NOT widgets in subdirectories
# Pattern matches: dashboards/<slug>/dashboard.json
# Excludes: dashboards/<slug>/widgets/*.json
if [[ ! "$FILE" =~ dashboards/[^/]+/dashboard\.json$ ]]; then
  # Not a dashboard file, skip validation
  exit 0
fi

# Check if file exists
if [[ ! -f "$FILE" ]]; then
  exit 0
fi

# Skip validation for placeholder files (content is just {})
# This prevents log pollution when scaffolding directory structures
FILE_CONTENT=$(cat "$FILE" | tr -d '[:space:]')
if [[ "$FILE_CONTENT" == "{}" ]]; then
  exit 0
fi

# Setup logging directory and file
WORKSPACE_DIR="$(pwd)"
LOGS_DIR="${WORKSPACE_DIR}/logs"
HOOK_LOG_FILE="${LOGS_DIR}/validation-hooks.jsonl"

# Create logs directory if it doesn't exist
mkdir -p "${LOGS_DIR}" 2>/dev/null || true

# Validate dashboard
echo "Validating dashboard: $FILE"

# Run validation script WITHOUT quiet mode to capture full output for logging
set +e
VALIDATION_OUTPUT=$(python "${CLAUDE_PLUGIN_ROOT}/scripts/dashboard/validate_dashboard.py" . "$FILE" --no-api 2>&1)
EXIT_CODE=$?
set -e

# Log validation result to JSONL file
# Export variables for Python subprocess and use heredoc to handle multiline output safely
export VALIDATION_OUTPUT EXIT_CODE FILE
python3 << 'PYEOF' >> "${HOOK_LOG_FILE}" 2>/dev/null || true
import json
import os
from datetime import datetime

validation_output = os.environ.get('VALIDATION_OUTPUT', '')
exit_code = int(os.environ.get('EXIT_CODE', '1'))
file_path = os.environ.get('FILE', '')

log_entry = {
    'timestamp': datetime.utcnow().isoformat() + 'Z',
    'hook': 'dashboard_validation',
    'file': file_path,
    'exit_code': exit_code,
    'status': 'success' if exit_code == 0 else 'error',
    'validation_output': validation_output if validation_output else None
}

print(json.dumps(log_entry))
PYEOF

if [ $EXIT_CODE -eq 0 ]; then
  # Validation passed
  echo "✓ Dashboard validation passed"
  exit 0
elif [ $EXIT_CODE -eq 2 ]; then
  # Validation failed - show the captured output
  echo "✗ Dashboard validation failed"
  echo ""
  echo "$VALIDATION_OUTPUT"
  exit 2
else
  # Fatal error - show the captured output
  echo "✗ Dashboard validation error (exit code: $EXIT_CODE)"
  echo ""
  echo "$VALIDATION_OUTPUT"
  exit 1
fi
