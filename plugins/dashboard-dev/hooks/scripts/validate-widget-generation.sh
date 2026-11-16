#!/bin/bash
# Post-generation validation hook for widget files
# Runs full 3-stage validation: Structure → Semantic → API (Final Authority)
#
# Exit codes:
#   0 - Validation passed OR unrecoverable error (model informed)
#   2 - Validation failed (stderr fed back to Claude for fixing)
#
# Response format from validate_widget.py (--quiet mode):
# {
#   "valid": true|false,
#   "stage_failed": "structure"|"semantic"|"api"|"parse"|null,
#   "errors": [{"rule_id": "...", "message": "...", "suggestion": "..."}],
#   "warnings": [...]
# }

set -e

# Read input from stdin (hook receives JSON context)
input=$(cat)
TOOL_PATH=$(echo "$input" | jq -r '.tool_input.file_path // empty')

# Only validate files in widgets/ directory
if [[ ! "$TOOL_PATH" =~ widgets/.*\.json$ ]]; then
    exit 0
fi

WIDGET_FILE="$TOOL_PATH"

# Check if file exists
if [[ ! -f "$WIDGET_FILE" ]]; then
    exit 0
fi

# Skip validation for placeholder files (content is just {})
# This prevents log pollution when scaffolding directory structures
FILE_CONTENT=$(cat "$WIDGET_FILE" | tr -d '[:space:]')
if [[ "$FILE_CONTENT" == "{}" ]]; then
    exit 0
fi

# Setup logging directory and file
WORKSPACE_DIR="$(pwd)"
LOGS_DIR="${WORKSPACE_DIR}/logs"
HOOK_LOG_FILE="${LOGS_DIR}/validation-hooks.jsonl"

# Create logs directory if it doesn't exist
mkdir -p "${LOGS_DIR}" 2>/dev/null || true

# Run full validation
set +e
VALIDATION_OUTPUT=$(python "${CLAUDE_PLUGIN_ROOT}/scripts/widget/validate_widget.py" . \
    "$WIDGET_FILE" \
    --quiet 2>&1)
VALIDATION_EXIT=$?
set -e

# Log validation output to JSONL file
python3 -c "
import json
import sys
from datetime import datetime

try:
    # Try to parse validation output as JSON
    validation_result = json.loads('''$VALIDATION_OUTPUT''')
except:
    validation_result = None

log_entry = {
    'timestamp': datetime.utcnow().isoformat() + 'Z',
    'hook': 'widget_validation',
    'file': '''$WIDGET_FILE''',
    'exit_code': $VALIDATION_EXIT,
    'status': 'success' if $VALIDATION_EXIT == 0 else 'error',
    'validation_result': validation_result,
    'raw_output': '''$VALIDATION_OUTPUT''' if validation_result is None else None
}

print(json.dumps(log_entry))
" >> "${HOOK_LOG_FILE}" 2>/dev/null || true

# Parse JSON response - check 'valid' field
VALID=$(echo "$VALIDATION_OUTPUT" | jq -r '.valid // false' 2>/dev/null || echo "false")

if [ "$VALID" != "true" ]; then
    # Extract all error rule_ids and messages for pattern matching
    ERROR_RULE_IDS=$(echo "$VALIDATION_OUTPUT" | jq -r '[.errors[]?.rule_id] | join(",")' 2>/dev/null || echo "")
    ERROR_MESSAGES=$(echo "$VALIDATION_OUTPUT" | jq -r '[.errors[]?.message] | join(" ")' 2>/dev/null || echo "")

    # -------------------------------------------------------------------------
    # Check for DATASET_PERMISSION_DENIED - cannot be fixed by agent
    # -------------------------------------------------------------------------
    if [[ "$ERROR_RULE_IDS" == *"DATASET_PERMISSION_DENIED"* ]]; then
        {
            echo ""
            echo "╔═══════════════════════════════════════════════════════════╗"
            echo "║        DATASET PERMISSION ERROR - CANNOT PROCEED          ║"
            echo "╚═══════════════════════════════════════════════════════════╝"
            echo ""
            echo "File: $WIDGET_FILE"
            echo ""
            echo "Dataset Access Denied:"
            echo "$VALIDATION_OUTPUT" | jq -r '.errors[]? | select(.rule_id == "DATASET_PERMISSION_DENIED") | "  \(.message)"' 2>/dev/null
            echo ""
            echo "Required Action:"
            echo "$VALIDATION_OUTPUT" | jq -r '.errors[]? | select(.rule_id == "DATASET_PERMISSION_DENIED") | "  \(.suggestion)"' 2>/dev/null
            echo ""
            echo "This error cannot be fixed by modifying widget code."
            echo "Contact your workspace administrator for dataset access."
            echo ""
            echo "Widget generation stopped. Resolve permissions before continuing."
            echo "═══════════════════════════════════════════════════════════"
        }
        exit 0  # Exit successfully to prevent agent retry loop
    fi

    # -------------------------------------------------------------------------
    # Check for CATALOG_ERROR - dataset does not exist
    # -------------------------------------------------------------------------
    if [[ "$ERROR_RULE_IDS" == *"CATALOG_ERROR"* ]] || [[ "$ERROR_MESSAGES" == *"does not exist"* ]] || [[ "$ERROR_MESSAGES" == *"Catalog"* ]]; then
        {
            echo ""
            echo "╔═══════════════════════════════════════════════════════════╗"
            echo "║          CATALOG ERROR - DATASET NOT FOUND                ║"
            echo "╚═══════════════════════════════════════════════════════════╝"
            echo ""
            echo "File: $WIDGET_FILE"
            echo ""
            echo "Error Details:"
            echo "$VALIDATION_OUTPUT" | jq -r '.errors[]? | select(.message | test("exist|Catalog"; "i")) | "  \(.message)"' 2>/dev/null
            echo ""
            echo "The referenced dataset does not exist in your organization."
            echo ""
            echo "Possible causes:"
            echo "  - Dataset name is misspelled"
            echo "  - Dataset does not exist in this workspace"
            echo "  - Dataset requires special permissions"
            echo ""
            echo "To see available datasets, run:"
            echo "  dashboard-sync dataset list --scope all"
            echo ""
            echo "This error cannot be fixed by modifying widget code."
            echo "═══════════════════════════════════════════════════════════"
        }
        exit 0  # Exit successfully to prevent agent retry loop
    fi

    # -------------------------------------------------------------------------
    # Default: Retriable error - output to stderr for Claude feedback
    # -------------------------------------------------------------------------
    {
        STAGE_FAILED=$(echo "$VALIDATION_OUTPUT" | jq -r '.stage_failed // "unknown"' 2>/dev/null)
        echo ""
        echo "═══════════════════════════════════════════════════════════"
        echo "Widget validation FAILED (stage: $STAGE_FAILED)"
        echo "═══════════════════════════════════════════════════════════"
        echo ""
        echo "File: $WIDGET_FILE"
        echo ""
        echo "Errors:"
        echo "$VALIDATION_OUTPUT" | jq -r '.errors[]? | "  [\(.rule_id)] \(.message)"' 2>/dev/null || echo "$VALIDATION_OUTPUT"
        echo ""
        echo "Suggestions:"
        echo "$VALIDATION_OUTPUT" | jq -r '.errors[]? | select(.suggestion != null) | "  → \(.suggestion)"' 2>/dev/null || true
        echo ""
        echo "Fix these errors and re-save the widget."
        echo "═══════════════════════════════════════════════════════════"
    } >&2
    exit 2  # Feed errors back to Claude
fi

# Validation passed - check for warnings
WARNING_COUNT=$(echo "$VALIDATION_OUTPUT" | jq -r '.warnings | length' 2>/dev/null || echo "0")

if [ "$WARNING_COUNT" -gt 0 ]; then
    echo "Widget validated with $WARNING_COUNT warning(s): $WIDGET_FILE"
    echo "$VALIDATION_OUTPUT" | jq -r '.warnings[]? | "  [\(.rule_id)] \(.message)"' 2>/dev/null || true
else
    echo "Widget validation passed: $WIDGET_FILE"
fi

exit 0
