#!/usr/bin/env bash
set -euo pipefail

# SessionStart Hook: Auto-generate config.yaml and bootstrap workspace
# Uses dashboard-dev.settings.md as single source of truth for state

WORKSPACE_ROOT="$(pwd)"
CONFIG_FILE="${WORKSPACE_ROOT}/config.yaml"
ENV_FILE="${WORKSPACE_ROOT}/.env"

# Get script directory for sourcing helper
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLAUDE_PLUGIN_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
export CLAUDE_PLUGIN_ROOT

# Source settings helper
source "${SCRIPT_DIR}/settings-helper.sh"

# Function: Check if config.yaml exists
check_config_exists() {
    [[ -f "$CONFIG_FILE" ]]
}

# Function: Check if .env exists with required credentials
check_credentials_exist() {
    if [[ ! -f "$ENV_FILE" ]]; then
        return 1
    fi

    # Check for DEVREV_PAT and DEVREV_ENDPOINT
    grep -q "^DEVREV_PAT=" "$ENV_FILE" 2>/dev/null && \
    grep -q "^DEVREV_ENDPOINT=" "$ENV_FILE" 2>/dev/null
}

# Function: Check if dashboard-sync CLI is available
check_cli_available() {
    command -v dashboard-sync >/dev/null 2>&1
}

# Function: Check if workspace has been bootstrapped
check_workspace_bootstrapped() {
    is_bootstrapped
}

# Note: Bootstrap functions removed - now handled by bootstrap-runner.sh
# which uses settings-helper.sh to read/write state to dashboard-dev.settings.md

# Main Logic
main() {
    # Initialize bootstrap tracking variables
    BOOTSTRAP_DATASETS_SUCCESS=0
    BOOTSTRAP_DATASETS_FAILED=()
    BOOTSTRAP_DASHBOARDS_SUCCESS=0
    BOOTSTRAP_DASHBOARDS_NAMES=()

    # If CLI not available, skip silently
    if ! check_cli_available; then
        exit 0
    fi

    # If config.yaml doesn't exist, try to create it
    if ! check_config_exists; then
        # If no credentials, warn user prominently
        if ! check_credentials_exist; then
            echo ""
            echo "⚠️  Environment not configured"
            echo ""
            if [[ ! -f "$ENV_FILE" ]]; then
                echo "   Missing: .env file"
                echo ""
                echo "   Setup steps:"
                echo "   1. cp .env.example .env"
                echo "   2. Add your DEVREV_PAT and DEVREV_ENDPOINT"
                echo "   3. Restart Claude Code session"
            else
                echo "   .env exists but missing required variables:"
                echo "   - DEVREV_PAT"
                echo "   - DEVREV_ENDPOINT"
                echo ""
                echo "   Add these to .env and restart session"
            fi
            echo ""
            exit 0
        fi

        # Generate config.yaml
        echo ""
        echo "🔧 Initializing workspace..."
        echo ""

        OUTPUT=$(dashboard-sync config init 2>&1)
        EXIT_CODE=$?

        if [[ $EXIT_CODE -eq 0 ]]; then
            echo "$OUTPUT"
            echo ""
        else
            echo "$OUTPUT"
            echo ""
            echo "⚠️  Could not auto-generate config.yaml"
            echo "   Try manually: dashboard-sync config init"
            echo ""
            exit 0
        fi
    fi

    # Auto-bootstrap in background if needed
    if check_config_exists && check_credentials_exist && needs_bootstrap; then
        # Update settings to in_progress before launching
        update_bootstrap_status "in_progress"

        echo ""
        echo "📦 Bootstrapping workspace in background..."
        echo ""

        # Launch bootstrap runner fully detached
        BOOTSTRAP_RUNNER="${SCRIPT_DIR}/bootstrap-runner.sh"
        nohup "$BOOTSTRAP_RUNNER" "$WORKSPACE_ROOT" </dev/null >/dev/null 2>&1 &
        disown

        echo "✓ Bootstrap started (check .claude/dashboard-dev.local.md for status)"
        echo ""
    fi

    # Always exit 0 (non-blocking)
    exit 0
}

main "$@"
