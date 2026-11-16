#!/usr/bin/env python3
"""
DevRev API client for making authenticated requests.

Usage:
    # List datasets
    python devrev_api.py oasis.dataset.list

    # Get a specific dataset
    python devrev_api.py oasis.dataset.get --name fact_ticket

    # Create a PaaS job
    python devrev_api.py serengeti.jobs.create --data '{"name": "my_job", ...}'

    # Execute a job
    python devrev_api.py serengeti.jobs.execute --data '{"id": "don:data:..."}'

    # Check job status (single check)
    python devrev_api.py jobs.get --id "don:core:..."

    # For polling job status until completion, use job_status.py:
    python job_status.py "don:core:..." --poll
"""

import argparse
import json
import os
import sys
from typing import Optional, Dict, Any

try:
    import requests
except ImportError:
    print("Error: requests library not installed. Run: pip install requests", file=sys.stderr)
    sys.exit(1)

from pat_decoder import load_pat_from_env, get_environment_from_pat, clean_pat_token


class DevRevAPIClient:
    """Client for making authenticated DevRev API requests."""

    def __init__(self, pat: Optional[str] = None, env_file: Optional[str] = None):
        """
        Initialize the API client.

        Args:
            pat: Optional PAT token. If not provided, loads from env/file.
            env_file: Path to .env file (auto-searches if not specified).
        """
        raw_pat = pat or load_pat_from_env(env_file)
        self.pat = clean_pat_token(raw_pat)
        self.env, self.api_url = get_environment_from_pat(self.pat)

        self.session = requests.Session()
        auth_header = self.pat if self.pat.startswith('Bearer ') else f'Bearer {self.pat}'
        self.session.headers.update({
            'Authorization': auth_header,
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        })

    def _build_url(self, endpoint: str) -> str:
        """Build full URL for an endpoint."""
        # Ensure endpoint starts with /
        if not endpoint.startswith('/'):
            endpoint = f'/internal/{endpoint}'
        elif not endpoint.startswith('/internal/'):
            endpoint = f'/internal{endpoint}'
        return f"{self.api_url}{endpoint}"

    def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Make a GET request.

        Args:
            endpoint: API endpoint (e.g., "oasis.dataset.list")
            params: Optional query parameters

        Returns:
            Response JSON as dictionary.
        """
        url = self._build_url(endpoint)
        response = self.session.get(url, params=params)
        response.raise_for_status()
        return response.json()

    def post(self, endpoint: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Make a POST request.

        Args:
            endpoint: API endpoint (e.g., "serengeti.jobs.create")
            data: Request body as dictionary

        Returns:
            Response JSON as dictionary.
        """
        url = self._build_url(endpoint)
        response = self.session.post(url, json=data or {})
        response.raise_for_status()
        return response.json()


# API endpoint definitions with their HTTP methods and parameters
API_ENDPOINTS = {
    # Oasis Dataset APIs
    "oasis.dataset.list": {"method": "GET", "params": []},
    "oasis.dataset.get": {"method": "GET", "params": ["name"]},
    "oasis.dataset.create": {"method": "POST", "data_required": True},
    "oasis.dataset.update": {"method": "POST", "data_required": True},
    "oasis.dataset.delete": {"method": "POST", "data_required": True},

    # Oasis Data APIs
    "oasis.data.fetch": {"method": "POST", "data_required": True},
    "oasis.data.put": {"method": "POST", "data_required": True},

    # PaaS (Serengeti) Job APIs
    "serengeti.jobs.list": {"method": "GET", "params": []},
    "serengeti.jobs.get": {"method": "GET", "params": ["id"]},
    "serengeti.jobs.create": {"method": "POST", "data_required": True},
    "serengeti.jobs.update": {"method": "POST", "data_required": True},
    "serengeti.jobs.execute": {"method": "POST", "data_required": True},
    "serengeti.jobs.delete": {"method": "POST", "data_required": True},

    # Job Status API
    "jobs.get": {"method": "GET", "params": ["id"]},
}


def main():
    """Command line interface for DevRev API."""
    parser = argparse.ArgumentParser(
        description="DevRev API client for dataset and job management",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List all datasets
  python devrev_api.py oasis.dataset.list

  # Get a specific dataset
  python devrev_api.py oasis.dataset.get --name fact_ticket

  # List PaaS jobs
  python devrev_api.py serengeti.jobs.list

  # Create a dataset
  python devrev_api.py oasis.dataset.create --data '{"name": "my_dataset", "columns": [...]}'

  # Create and execute a PaaS job
  python devrev_api.py serengeti.jobs.create --data '{"name": "my_job", "queries": [...], "publishers": [...]}'
  python devrev_api.py serengeti.jobs.execute --data '{"id": "don:data:dvrv-us-1:devo/787:oasis_job/123"}'

  # Check job execution status
  python devrev_api.py jobs.get --id "don:core:dvrv-us-1:devo/787:job/456"
"""
    )

    parser.add_argument("endpoint", choices=list(API_ENDPOINTS.keys()),
                        help="API endpoint to call")
    parser.add_argument("--name", help="Name parameter (for dataset.get)")
    parser.add_argument("--id", help="ID parameter (for jobs.get, serengeti.jobs.get)")
    parser.add_argument("--data", help="JSON data for POST requests")
    parser.add_argument("--data-file", help="Path to JSON file with request data")
    parser.add_argument("--env-file", default=None, help="Path to .env file (auto-searches if not specified)")
    parser.add_argument("--pretty", action="store_true", default=True,
                        help="Pretty print JSON output (default: true)")

    args = parser.parse_args()

    try:
        # Initialize client
        client = DevRevAPIClient(env_file=args.env_file)

        endpoint_config = API_ENDPOINTS[args.endpoint]
        method = endpoint_config["method"]

        # Build request parameters
        if method == "GET":
            params = {}
            if args.name:
                params["name"] = args.name
            if args.id:
                params["id"] = args.id

            result = client.get(args.endpoint, params if params else None)

        else:  # POST
            data = None
            if args.data:
                data = json.loads(args.data)
            elif args.data_file:
                with open(args.data_file, 'r') as f:
                    data = json.load(f)
            elif endpoint_config.get("data_required"):
                print(f"Error: --data or --data-file required for {args.endpoint}", file=sys.stderr)
                sys.exit(1)

            result = client.post(args.endpoint, data)

        # Output result
        if args.pretty:
            print(json.dumps(result, indent=2))
        else:
            print(json.dumps(result))

    except requests.exceptions.HTTPError as e:
        error_response = {"error": str(e)}
        try:
            error_response["details"] = e.response.json()
        except:
            error_response["details"] = e.response.text
        print(json.dumps(error_response, indent=2), file=sys.stderr)
        sys.exit(1)

    except json.JSONDecodeError as e:
        print(json.dumps({"error": f"Invalid JSON: {e}"}), file=sys.stderr)
        sys.exit(1)

    except ValueError as e:
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        sys.exit(1)

    except Exception as e:
        print(json.dumps({"error": f"Unexpected error: {e}"}), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
