#!/bin/bash
#
# Setup Ponos testing environment
#
# This script handles:
# 1. AWS SSO login
# 2. Role assumption via shared repo script
# 3. Sourcing environment variables
#
# Usage:
#   source setup_ponos_env.sh --profile dev --shared-repo /path/to/shared
#
# Note: This script should be sourced, not executed, to preserve env vars
#

set -e

# Default values
AWS_PROFILE="dev"
SHARED_REPO=""
SERVICE="ponos"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --profile)
            AWS_PROFILE="$2"
            shift 2
            ;;
        --shared-repo)
            SHARED_REPO="$2"
            shift 2
            ;;
        --service)
            SERVICE="$2"
            shift 2
            ;;
        --help)
            echo "Usage: source setup_ponos_env.sh [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --profile PROFILE    AWS profile name (default: dev)"
            echo "  --shared-repo PATH   Path to devrev/shared repository"
            echo "  --service SERVICE    Service for role assumption (default: ponos)"
            echo ""
            echo "Example:"
            echo "  source setup_ponos_env.sh --profile dev --shared-repo ~/DevRev/shared"
            return 0 2>/dev/null || exit 0
            ;;
        *)
            echo "Unknown option: $1"
            return 1 2>/dev/null || exit 1
            ;;
    esac
done

# Validate shared repo path
if [[ -z "$SHARED_REPO" ]]; then
    echo "Error: --shared-repo is required"
    echo "Please provide the path to the devrev/shared repository"
    return 1 2>/dev/null || exit 1
fi

if [[ ! -d "$SHARED_REPO" ]]; then
    echo "Error: Shared repo not found at: $SHARED_REPO"
    echo "Clone it with: git clone https://github.com/devrev/shared.git"
    return 1 2>/dev/null || exit 1
fi

ROLE_SCRIPT="$SHARED_REPO/py/utils/aws_role_assumption/assume_service_role.py"
if [[ ! -f "$ROLE_SCRIPT" ]]; then
    echo "Error: Role assumption script not found at: $ROLE_SCRIPT"
    echo "Make sure the shared repo is up to date: git -C $SHARED_REPO pull"
    return 1 2>/dev/null || exit 1
fi

echo "=== Setting up Ponos Testing Environment ==="
echo ""

# Step 1: AWS SSO Login
echo "Step 1: AWS SSO Login"
echo "Profile: $AWS_PROFILE"
echo ""

# Check if already logged in
if aws sts get-caller-identity --profile "$AWS_PROFILE" &>/dev/null; then
    echo "Already logged in to AWS SSO"
    IDENTITY=$(aws sts get-caller-identity --profile "$AWS_PROFILE" --output text --query 'Arn')
    echo "Identity: $IDENTITY"
else
    echo "Logging in to AWS SSO..."
    aws sso login --profile "$AWS_PROFILE"

    if ! aws sts get-caller-identity --profile "$AWS_PROFILE" &>/dev/null; then
        echo "Error: AWS SSO login failed"
        return 1 2>/dev/null || exit 1
    fi
    echo "AWS SSO login successful"
fi

echo ""

# Step 2: Role Assumption
echo "Step 2: Service Role Assumption"
echo "Service: $SERVICE"
echo ""

# Run role assumption script
echo "Running: python3 $ROLE_SCRIPT -s $SERVICE --aws-profile $AWS_PROFILE"
if ! python3 "$ROLE_SCRIPT" -s "$SERVICE" --aws-profile "$AWS_PROFILE"; then
    echo ""
    echo "Warning: Role assumption failed."
    echo "This might be due to ACLSizePerRole limit."
    echo ""
    echo "Try running the cleanup script first:"
    echo "  python3 $SHARED_REPO/py/utils/aws_role_assumption/remove_role_trust.py -s $SERVICE --aws-profile $AWS_PROFILE"
    echo ""
    echo "Then re-run this script."
    return 1 2>/dev/null || exit 1
fi

echo ""

# Step 3: Source environment
echo "Step 3: Sourcing Environment Variables"
echo ""

ENV_FILES=(/tmp/.env*)
if [[ ${#ENV_FILES[@]} -eq 0 ]] || [[ ! -e "${ENV_FILES[0]}" ]]; then
    echo "Warning: No /tmp/.env* files found"
    echo "Role assumption may not have created the expected environment files"
else
    for env_file in /tmp/.env*; do
        if [[ -f "$env_file" ]]; then
            echo "Sourcing: $env_file"
            source "$env_file"
        fi
    done
    echo ""
    echo "Environment variables loaded"
fi

echo ""
echo "=== Setup Complete ==="
echo ""
echo "You can now run Ponos tests with:"
echo "  make int-test ARGS='--jobpaths=<your_job>.yaml --bqdryrun'"
echo ""
echo "For full tests:"
echo "  make int-test ARGS='--jobpaths=<your_job>.yaml'"
