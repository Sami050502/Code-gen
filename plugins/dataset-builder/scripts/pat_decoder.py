#!/usr/bin/env python3
"""
Module for decoding DevRev PAT tokens and determining environment.

Usage:
    python pat_decoder.py <PAT_TOKEN>
    python pat_decoder.py  # reads from DEVREV_PAT env var
"""

import base64
import json
import os
import sys
from typing import Tuple
from enum import Enum


class DevRevEnvironment(Enum):
    """DevRev environment types."""
    DEV = "dev"
    PROD = "prod"
    QA = "qa"


# Mapping of issuer URLs to environments
ISSUER_TO_ENV = {
    "https://auth-token.dev.devrev-eng.ai/": DevRevEnvironment.DEV,
    "https://auth-token.devrev.ai/": DevRevEnvironment.PROD,
    "https://auth-token.qa.devrev-eng.ai/": DevRevEnvironment.QA,
}

# Mapping of environments to API URLs
ENV_TO_API_URL = {
    DevRevEnvironment.DEV: "https://api.dev.devrev-eng.ai",
    DevRevEnvironment.PROD: "https://api.devrev.ai",
    DevRevEnvironment.QA: "https://api.qa.devrev-eng.ai",
}


def clean_pat_token(token: str) -> str:
    """
    Clean a PAT token by removing common artifacts from copy-paste.

    Args:
        token: The raw PAT token string.

    Returns:
        Cleaned token string.
    """
    # Strip whitespace and newlines
    token = token.strip()

    # Remove 'Bearer ' prefix if present
    if token.lower().startswith('bearer '):
        token = token[7:].strip()

    # Remove quotes if wrapped
    if (token.startswith('"') and token.endswith('"')) or \
       (token.startswith("'") and token.endswith("'")):
        token = token[1:-1]

    # Remove any trailing special characters that may have been added
    # JWT tokens end with base64 characters (alphanumeric, -, _, =)
    import re
    # Find where the valid JWT ends (3 parts separated by dots)
    parts = token.split('.')
    if len(parts) >= 3:
        # Clean each part - keep only valid base64url characters
        cleaned_parts = []
        for i, part in enumerate(parts[:3]):
            # Base64url uses A-Za-z0-9-_=
            cleaned = re.sub(r'[^A-Za-z0-9\-_=]', '', part)
            cleaned_parts.append(cleaned)
        token = '.'.join(cleaned_parts)

    return token


def decode_jwt_payload(token: str) -> dict:
    """
    Decode the payload portion of a JWT token without verification.

    Args:
        token: The JWT token string.

    Returns:
        The decoded payload as a dictionary.

    Raises:
        ValueError: If the token is not a valid JWT format.
    """
    token = clean_pat_token(token)
    parts = token.split('.')
    if len(parts) != 3:
        raise ValueError("Invalid JWT token format: expected 3 parts separated by '.'")

    payload_b64 = parts[1]

    # Add padding if necessary (JWT uses base64url encoding without padding)
    padding_needed = 4 - (len(payload_b64) % 4)
    if padding_needed != 4:
        payload_b64 += '=' * padding_needed

    try:
        # Replace URL-safe characters
        payload_b64 = payload_b64.replace('-', '+').replace('_', '/')
        payload_json = base64.b64decode(payload_b64).decode('utf-8')
        return json.loads(payload_json)
    except Exception as e:
        raise ValueError(f"Failed to decode JWT payload: {e}")


def decode_jwt_header(token: str) -> dict:
    """
    Decode the header portion of a JWT token without verification.

    Args:
        token: The JWT token string.

    Returns:
        The decoded header as a dictionary.

    Raises:
        ValueError: If the token is not a valid JWT format.
    """
    token = clean_pat_token(token)
    parts = token.split('.')
    if len(parts) != 3:
        raise ValueError("Invalid JWT token format: expected 3 parts separated by '.'")

    header_b64 = parts[0]

    # Add padding if necessary
    padding_needed = 4 - (len(header_b64) % 4)
    if padding_needed != 4:
        header_b64 += '=' * padding_needed

    try:
        header_b64 = header_b64.replace('-', '+').replace('_', '/')
        header_json = base64.b64decode(header_b64).decode('utf-8')
        return json.loads(header_json)
    except Exception as e:
        raise ValueError(f"Failed to decode JWT header: {e}")


def get_environment_from_pat(pat: str) -> Tuple[DevRevEnvironment, str]:
    """
    Determine the DevRev environment from a PAT token.

    Args:
        pat: The DevRev Personal Access Token.

    Returns:
        A tuple of (DevRevEnvironment, api_url).

    Raises:
        ValueError: If the environment cannot be determined from the token.
    """
    header = decode_jwt_header(pat)

    issuer = header.get('iss')
    if not issuer:
        raise ValueError("JWT header does not contain 'iss' (issuer) claim")

    # Normalize issuer URL (ensure trailing slash)
    if not issuer.endswith('/'):
        issuer += '/'

    env = ISSUER_TO_ENV.get(issuer)
    if env is None:
        raise ValueError(f"Unknown issuer: {issuer}. Expected one of: {list(ISSUER_TO_ENV.keys())}")

    api_url = ENV_TO_API_URL[env]

    return env, api_url


def get_dev_oid_from_pat(pat: str) -> str:
    """
    Extract the dev_oid (organization ID) from a PAT token.

    Args:
        pat: The DevRev Personal Access Token.

    Returns:
        The dev_oid string (e.g., "DEV-787").

    Raises:
        ValueError: If dev_oid cannot be extracted.
    """
    payload = decode_jwt_payload(pat)

    # The dev_oid is typically in the 'aud' claim or 'dev_oid' claim
    dev_oid = payload.get('dev_oid')
    if dev_oid:
        return dev_oid

    # Try to extract from 'aud' (audience) claim
    aud = payload.get('aud')
    if aud and isinstance(aud, str) and aud.startswith('DEV-'):
        return aud

    raise ValueError("Could not extract dev_oid from PAT token")


def find_env_file() -> str | None:
    """
    Search for .env file containing DEVREV_PAT in multiple locations.

    Returns:
        Path to .env file if found, None otherwise.
    """
    import pathlib

    def has_devrev_pat(path: str) -> bool:
        """Check if file contains DEVREV_PAT."""
        try:
            with open(path, 'r') as f:
                return any(line.strip().startswith('DEVREV_PAT=') for line in f)
        except (OSError, IOError):
            return False

    # 1. Check current directory
    if os.path.exists(".env") and has_devrev_pat(".env"):
        return os.path.abspath(".env")

    # 2. Check parent directories (up to 5 levels)
    current = pathlib.Path.cwd()
    for _ in range(5):
        parent = current.parent
        env_path = parent / ".env"
        if env_path.exists() and has_devrev_pat(str(env_path)):
            return str(env_path)
        if parent == current:  # Reached root
            break
        current = parent

    # 3. Check home directory
    home_env = os.path.expanduser("~/.env")
    if os.path.exists(home_env) and has_devrev_pat(home_env):
        return home_env

    # 4. Check common DevRev project locations
    common_locations = [
        os.path.expanduser("~/DevRev/aai-skills/.env"),
        os.path.expanduser("~/devrev/aai-skills/.env"),
    ]
    for loc in common_locations:
        if os.path.exists(loc) and has_devrev_pat(loc):
            return loc

    return None


def load_pat_from_env(env_file: str | None = None) -> str:
    """
    Load PAT from environment variable or .env file.

    Searches for .env file in multiple locations:
    1. Environment variable DEVREV_PAT
    2. Current directory
    3. Parent directories (up to 5 levels)
    4. Home directory
    5. Common DevRev project locations

    Args:
        env_file: Optional explicit path to .env file

    Returns:
        The PAT token string.

    Raises:
        ValueError: If PAT cannot be found.
    """
    # First try environment variable
    pat = os.environ.get('DEVREV_PAT')
    if pat:
        return pat.strip()

    # Find .env file if not specified
    if env_file is None:
        env_file = find_env_file()

    if env_file is None:
        raise ValueError(
            "DEVREV_PAT not found. Searched:\n"
            "  - DEVREV_PAT environment variable\n"
            "  - .env in current and parent directories\n"
            "  - ~/.env\n"
            "  - ~/DevRev/aai-skills/.env"
        )

    # Load from .env file
    with open(env_file, 'r') as f:
        for line in f:
            line = line.strip()
            if line.startswith('DEVREV_PAT='):
                pat = line.split('=', 1)[1].strip()
                # Remove quotes if present
                if (pat.startswith('"') and pat.endswith('"')) or \
                   (pat.startswith("'") and pat.endswith("'")):
                    pat = pat[1:-1]
                return pat

    raise ValueError(f"DEVREV_PAT not found in {env_file}")


def main():
    """Command line interface for PAT decoder."""
    try:
        # Get PAT from argument or environment
        if len(sys.argv) > 1:
            pat = sys.argv[1]
        else:
            pat = load_pat_from_env()

        env, api_url = get_environment_from_pat(pat)

        # Try to get dev_oid
        try:
            dev_oid = get_dev_oid_from_pat(pat)
        except ValueError:
            dev_oid = "unknown"

        # Output as JSON for easy parsing
        result = {
            "environment": env.value,
            "api_url": api_url,
            "dev_oid": dev_oid
        }

        print(json.dumps(result, indent=2))

    except ValueError as e:
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(json.dumps({"error": f"Unexpected error: {e}"}), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
