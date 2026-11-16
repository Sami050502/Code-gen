#!/usr/bin/env bash
# Background bootstrap runner - uses dashboard-dev.settings.md for state
set +e  # Don't exit on errors

WORKSPACE_ROOT="${1:-$(pwd)}"

# Set CLAUDE_PLUGIN_ROOT for settings helper
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLAUDE_PLUGIN_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
export CLAUDE_PLUGIN_ROOT

# Source settings helper
source "${SCRIPT_DIR}/settings-helper.sh"

# Initialize tracking variables
BOOTSTRAP_DATASETS_SUCCESS=0
BOOTSTRAP_DATASETS_FAILED=()
BOOTSTRAP_DASHBOARDS_SUCCESS=0
BOOTSTRAP_DASHBOARDS_NAMES=()

# Get core resources from settings (portable for bash 3.x and zsh)
CORE_DATASETS=()
while IFS= read -r line; do
    CORE_DATASETS+=("$line")
done < <(get_core_datasets)

CORE_DASHBOARDS=()
while IFS= read -r line; do
    CORE_DASHBOARDS+=("$line")
done < <(get_core_dashboards)

# Bootstrap datasets
for dataset in "${CORE_DATASETS[@]}"; do
    output=$(dashboard-sync dataset fetch "$dataset" 2>&1)
    if echo "$output" | grep -q "Schema saved to"; then
        ((BOOTSTRAP_DATASETS_SUCCESS++))
    else
        BOOTSTRAP_DATASETS_FAILED+=("$dataset")
    fi
done

# Bootstrap dashboards
dashboard_list=$(dashboard-sync dashboard list 2>&1)

if echo "$dashboard_list" | grep -q "dashboards:"; then
    dashboard_ids=()

    for name in "${CORE_DASHBOARDS[@]}"; do
        id=$(echo "$dashboard_list" | grep -F "$name" | head -1 | awk '{print $1}')
        if [[ -n "$id" && "$id" =~ ^[a-zA-Z0-9]{10}$ ]]; then
            dashboard_ids+=("$id")
            BOOTSTRAP_DASHBOARDS_NAMES+=("$name")
        fi
    done

    if [[ ${#dashboard_ids[@]} -gt 0 ]]; then
        ids_csv=$(IFS=,; echo "${dashboard_ids[*]}")
        output=$(dashboard-sync dashboard download "$ids_csv" --skip-existing 2>&1)
        BOOTSTRAP_DASHBOARDS_SUCCESS=$(echo "$output" | grep -c "✓" || echo "0")
    fi
fi

# Update settings with results
update_bootstrap_results "$BOOTSTRAP_DATASETS_SUCCESS" "$BOOTSTRAP_DASHBOARDS_SUCCESS" "${BOOTSTRAP_DATASETS_FAILED[@]}"
update_bootstrap_status "complete"
