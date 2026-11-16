#!/usr/bin/env bash
#
# Check prerequisites for dataset-builder plugin
# Compatible with bash 3.2+ (macOS default)
#
# Usage: ./check_prerequisites.sh [--json]
#

JSON_OUTPUT=false
if [[ "$1" == "--json" ]]; then
    JSON_OUTPUT=true
fi

# Results stored as simple variables
result_python=""
result_gcloud=""
result_bq=""
result_aws_cli=""
result_kubectl=""
result_git=""
result_python_requests=""
result_aws_config=""
result_devrev_pat=""
result_gcloud_auth=""
result_aws_sso_login=""
result_kubectl_context=""

check_command() {
    local cmd="$1"
    local version_cmd="$2"

    if command -v "$cmd" &> /dev/null; then
        if [[ -n "$version_cmd" ]]; then
            version=$(eval "$version_cmd" 2>/dev/null | head -1 || echo "installed")
        else
            version="installed"
        fi
        echo "ok:$version"
    else
        echo "missing"
    fi
}

# Check required tools
result_python=$(check_command "python3" "python3 --version")
result_gcloud=$(check_command "gcloud" "gcloud --version | head -1")
result_bq=$(check_command "bq" "bq version 2>/dev/null | head -1")
result_aws_cli=$(check_command "aws" "aws --version")
result_kubectl=$(check_command "kubectl" "kubectl version --client --short 2>/dev/null || echo installed")
result_git=$(check_command "git" "git --version")

# Check Python packages
if python3 -c "import requests" 2>/dev/null; then
    result_python_requests="ok:installed"
else
    result_python_requests="missing"
fi

# Check AWS config
if [[ -f "$HOME/.aws/config" ]]; then
    result_aws_config="ok:exists"
else
    result_aws_config="missing"
fi

# Check for .env file with DEVREV_PAT in multiple locations
find_devrev_pat() {
    # 1. Check environment variable first
    if [[ -n "$DEVREV_PAT" ]]; then
        echo "ok:env_var"
        return
    fi

    # 2. Check current directory
    if [[ -f ".env" ]] && grep -q "DEVREV_PAT" ".env" 2>/dev/null; then
        echo "ok:$(pwd)/.env"
        return
    fi

    # 3. Check parent directories (up to 5 levels)
    local dir="$(pwd)"
    for _ in 1 2 3 4 5; do
        dir="$(dirname "$dir")"
        if [[ -f "$dir/.env" ]] && grep -q "DEVREV_PAT" "$dir/.env" 2>/dev/null; then
            echo "ok:$dir/.env"
            return
        fi
        [[ "$dir" == "/" ]] && break
    done

    # 4. Check home directory
    if [[ -f "$HOME/.env" ]] && grep -q "DEVREV_PAT" "$HOME/.env" 2>/dev/null; then
        echo "ok:$HOME/.env"
        return
    fi

    # 5. Check common DevRev project locations
    for loc in "$HOME/DevRev/aai-skills" "$HOME/devrev/aai-skills"; do
        if [[ -f "$loc/.env" ]] && grep -q "DEVREV_PAT" "$loc/.env" 2>/dev/null; then
            echo "ok:$loc/.env"
            return
        fi
    done

    echo "missing"
}

result_devrev_pat=$(find_devrev_pat)

# Check gcloud auth
if command -v gcloud &>/dev/null && gcloud auth list --filter="status:ACTIVE" --format="value(account)" 2>/dev/null | grep -q "@"; then
    result_gcloud_auth="ok:authenticated"
else
    result_gcloud_auth="missing"
fi

# Check AWS SSO login status (best effort)
if command -v aws &>/dev/null && aws sts get-caller-identity --profile dev &>/dev/null; then
    result_aws_sso_login="ok:authenticated"
else
    result_aws_sso_login="missing"
fi

# Check kubectl context
if command -v kubectl &>/dev/null && kubectl config current-context &>/dev/null; then
    context=$(kubectl config current-context 2>/dev/null)
    result_kubectl_context="ok:$context"
else
    result_kubectl_context="missing"
fi

# Helper to extract status
get_status() {
    echo "${1%%:*}"
}

get_detail() {
    echo "${1#*:}"
}

# Output results
if $JSON_OUTPUT; then
    cat <<EOF
{
  "python": {"status": "$(get_status "$result_python")", "detail": "$(get_detail "$result_python")"},
  "gcloud": {"status": "$(get_status "$result_gcloud")", "detail": "$(get_detail "$result_gcloud")"},
  "bq": {"status": "$(get_status "$result_bq")", "detail": "$(get_detail "$result_bq")"},
  "aws_cli": {"status": "$(get_status "$result_aws_cli")", "detail": "$(get_detail "$result_aws_cli")"},
  "kubectl": {"status": "$(get_status "$result_kubectl")", "detail": "$(get_detail "$result_kubectl")"},
  "git": {"status": "$(get_status "$result_git")", "detail": "$(get_detail "$result_git")"},
  "python_requests": {"status": "$(get_status "$result_python_requests")", "detail": "$(get_detail "$result_python_requests")"},
  "aws_config": {"status": "$(get_status "$result_aws_config")", "detail": "$(get_detail "$result_aws_config")"},
  "devrev_pat": {"status": "$(get_status "$result_devrev_pat")", "detail": "$(get_detail "$result_devrev_pat")"},
  "gcloud_auth": {"status": "$(get_status "$result_gcloud_auth")", "detail": "$(get_detail "$result_gcloud_auth")"},
  "aws_sso_login": {"status": "$(get_status "$result_aws_sso_login")", "detail": "$(get_detail "$result_aws_sso_login")"},
  "kubectl_context": {"status": "$(get_status "$result_kubectl_context")", "detail": "$(get_detail "$result_kubectl_context")"}
}
EOF
else
    echo "=== Dataset Builder Prerequisites Check ==="
    echo ""

    echo "REQUIRED TOOLS:"
    for item in "python:$result_python" "gcloud:$result_gcloud" "bq:$result_bq" "aws_cli:$result_aws_cli" "kubectl:$result_kubectl" "git:$result_git"; do
        name="${item%%:*}"
        rest="${item#*:}"
        status=$(get_status "$rest")
        detail=$(get_detail "$rest")
        if [[ "$status" == "ok" ]]; then
            echo "  [OK] $name: $detail"
        else
            echo "  [MISSING] $name"
        fi
    done

    echo ""
    echo "PYTHON PACKAGES:"
    if [[ "$(get_status "$result_python_requests")" == "ok" ]]; then
        echo "  [OK] requests library"
    else
        echo "  [MISSING] requests library - run: pip install requests"
    fi

    echo ""
    echo "CONFIGURATION:"
    for item in "aws_config:$result_aws_config" "devrev_pat:$result_devrev_pat" "gcloud_auth:$result_gcloud_auth" "aws_sso_login:$result_aws_sso_login" "kubectl_context:$result_kubectl_context"; do
        name="${item%%:*}"
        rest="${item#*:}"
        status=$(get_status "$rest")
        detail=$(get_detail "$rest")
        if [[ "$status" == "ok" ]]; then
            echo "  [OK] $name: $detail"
        else
            echo "  [MISSING] $name"
        fi
    done

    echo ""

    # Count missing
    missing_count=0
    for result in "$result_python" "$result_gcloud" "$result_bq" "$result_aws_cli" "$result_kubectl" "$result_git" "$result_python_requests" "$result_aws_config" "$result_devrev_pat" "$result_gcloud_auth" "$result_aws_sso_login" "$result_kubectl_context"; do
        if [[ "$(get_status "$result")" == "missing" ]]; then
            ((missing_count++)) || true
        fi
    done

    if [[ $missing_count -eq 0 ]]; then
        echo "All prerequisites satisfied!"
        exit 0
    else
        echo "Missing prerequisites: $missing_count"
        echo "Run /dataset-builder:setup for guided configuration."
        exit 1
    fi
fi
