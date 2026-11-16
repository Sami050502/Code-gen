#!/usr/bin/env bash
# Settings file helper functions for dashboard-dev plugin

# Settings file is in workspace .claude directory (per-project)
SETTINGS_FILE="${PWD}/.claude/dashboard-dev.local.md"

# Extract YAML frontmatter value
get_setting() {
    local key="$1"
    local default="${2:-}"

    if [[ ! -f "$SETTINGS_FILE" ]]; then
        echo "$default"
        return 1
    fi

    # Extract value from YAML frontmatter (between first and second ---)
    local value
    value=$(awk -v key="$key" -v default="$default" '
        BEGIN { in_yaml = 0; found = 0 }
        /^---$/ { in_yaml = !in_yaml; next }
        in_yaml && $0 ~ "^" key ":" {
            sub("^" key ": *", "")
            # Remove comments
            sub(/ *#.*$/, "")
            # Remove quotes
            gsub(/^["'\'']/, "")
            gsub(/["'\'']$/, "")
            # Trim whitespace
            gsub(/^ +| +$/, "")
            print
            found = 1
            exit
        }
        END { if (!found) print default }
    ' "$SETTINGS_FILE")

    echo "$value"
}

# Check if bootstrap is needed
needs_bootstrap() {
    local boot_status=$(get_setting "  status" "pending")
    local auto_bootstrap=$(get_setting "auto_bootstrap" "true")

    [[ "$boot_status" == "pending" && "$auto_bootstrap" == "true" ]]
}

# Check if bootstrap is complete
is_bootstrapped() {
    local boot_status=$(get_setting "  status" "pending")
    [[ "$boot_status" == "complete" ]]
}

# Update bootstrap status in settings file
update_bootstrap_status() {
    local new_status="$1"
    local timestamp="$(date -Iseconds)"

    if [[ ! -f "$SETTINGS_FILE" ]]; then
        echo "Error: Settings file not found: $SETTINGS_FILE" >&2
        return 1
    fi

    # Use temp file for atomic update
    local temp_file="${SETTINGS_FILE}.tmp"

    awk -v status="$new_status" -v ts="$timestamp" '
        BEGIN { in_yaml = 0; yaml_marker = 0 }

        /^---$/ {
            yaml_marker++
            if (yaml_marker == 1) {
                in_yaml = 1
            } else if (yaml_marker == 2) {
                in_yaml = 0
            }
            print
            next
        }

        in_yaml && /^  status:/ {
            print "  status: " status
            next
        }

        in_yaml && /^  initialized_at:/ && status == "in_progress" {
            print "  initialized_at: \"" ts "\""
            next
        }

        in_yaml && /^  completed_at:/ && status == "complete" {
            print "  completed_at: \"" ts "\""
            next
        }

        { print }
    ' "$SETTINGS_FILE" > "$temp_file"

    mv "$temp_file" "$SETTINGS_FILE"
}

# Update bootstrap results in settings file
update_bootstrap_results() {
    local datasets_count="$1"
    local dashboards_count="$2"
    shift 2
    local failed_datasets=("$@")

    if [[ ! -f "$SETTINGS_FILE" ]]; then
        echo "Error: Settings file not found: $SETTINGS_FILE" >&2
        return 1
    fi

    local temp_file="${SETTINGS_FILE}.tmp"

    awk -v datasets="$datasets_count" -v dashboards="$dashboards_count" '
        BEGIN { in_yaml = 0; yaml_marker = 0; in_datasets = 0; in_dashboards = 0 }

        /^---$/ {
            yaml_marker++
            if (yaml_marker == 1) {
                in_yaml = 1
            } else if (yaml_marker == 2) {
                in_yaml = 0
            }
            print
            next
        }

        in_yaml && /^  datasets:/ {
            in_datasets = 1
            print
            next
        }

        in_yaml && in_datasets && /^    downloaded:/ {
            print "    downloaded: " datasets
            next
        }

        in_yaml && in_datasets && /^    failed:/ {
            in_datasets = 0
        }

        in_yaml && /^  dashboards:/ {
            in_dashboards = 1
            print
            next
        }

        in_yaml && in_dashboards && /^    downloaded:/ {
            print "    downloaded: " dashboards
            in_dashboards = 0
            next
        }

        { print }
    ' "$SETTINGS_FILE" > "$temp_file"

    mv "$temp_file" "$SETTINGS_FILE"
}

# Get list of core datasets from settings
get_core_datasets() {
    if [[ ! -f "$SETTINGS_FILE" ]]; then
        return 1
    fi

    sed -n '/^core_datasets:/,/^[a-z]/p' "$SETTINGS_FILE" | \
        grep '^  - ' | \
        sed 's/^  - //; s/"//g'
}

# Get list of core dashboards from settings
get_core_dashboards() {
    if [[ ! -f "$SETTINGS_FILE" ]]; then
        return 1
    fi

    sed -n '/^core_dashboards:/,/^[a-z]/p' "$SETTINGS_FILE" | \
        grep '^  - ' | \
        sed 's/^  - //; s/"//g'
}
