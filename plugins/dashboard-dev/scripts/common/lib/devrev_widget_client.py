"""
DevRev Widget and Dashboard API Client.
"""

import requests
from pathlib import Path
from typing import Dict, Any, Optional


class DevRevWidgetClient:
    """Client for DevRev widget and dashboard APIs."""

    def __init__(self, pat: Optional[str] = None, endpoint: Optional[str] = None, env_file: Optional[Path] = None):
        """
        Initialize DevRev Widget Client.

        Args:
            pat: Personal Access Token (required if env_file not provided)
            endpoint: API endpoint URL (required if env_file not provided)
            env_file: Path to .env file with DEVREV_PAT and DEVREV_ENDPOINT

        Raises:
            ValueError: If neither (pat, endpoint) nor env_file is provided
        """
        if env_file:
            # Load credentials from .env file
            self.pat, endpoint_raw = self._load_from_env(env_file)
            self.endpoint = endpoint_raw.rstrip('/')  # Remove trailing slash
        elif pat and endpoint:
            self.pat = pat
            self.endpoint = endpoint.rstrip('/')  # Remove trailing slash
        else:
            raise ValueError("Must provide either (pat, endpoint) or env_file")

    def _load_from_env(self, env_file: Path) -> tuple[str, str]:
        """Load credentials from .env file."""
        if not env_file.exists():
            raise ValueError(f".env file not found: {env_file}")

        env_vars = {}
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key.strip()] = value.strip().strip('"').strip("'")

        pat = env_vars.get('DEVREV_PAT')
        endpoint = env_vars.get('DEVREV_ENDPOINT', 'https://api.devrev.ai')

        if not pat:
            raise ValueError(f"DEVREV_PAT not found in {env_file}")

        return pat, endpoint

    def _make_request(self, method: str, url: str, json_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make HTTP request to DevRev API."""
        # Internal APIs use PAT directly, public APIs use "Bearer {pat}"
        is_internal = "/internal/" in url

        headers = {
            "Authorization": self.pat if is_internal else f"Bearer {self.pat}",
            "Content-Type": "application/json"
        }

        if method == "GET":
            response = requests.get(url, headers=headers)
        elif method == "POST":
            response = requests.post(url, headers=headers, json=json_data or {})
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")

        response.raise_for_status()
        return response.json()

    def validate_widget(self, widget_json: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate widget JSON via DevRev API.

        Args:
            widget_json: Complete widget JSON dictionary

        Returns:
            Validation result:
            - is_valid (bool): Whether widget is valid
            - type (str): Error type if invalid
            - field_name (str): Field name if invalid
            - debug_message (str): Error details if invalid

        Raises:
            requests.HTTPError: If API call fails
        """
        url = f"{self.endpoint}/internal/widgets.create.validate"

        # API expects inlined payload (no wrapper) per protobuf inline annotation
        try:
            result = self._make_request("POST", url, widget_json)
            # If no error, validation passed
            return {"is_valid": True}
        except requests.HTTPError as e:
            # Parse error response
            try:
                error_data = e.response.json()
                return {
                    "is_valid": False,
                    "type": error_data.get('type', 'unknown'),
                    "field_name": error_data.get('field_name'),
                    "debug_message": error_data.get('debug_message', str(e)),
                    "message": error_data.get('message', 'Validation failed')
                }
            except Exception:
                return {
                    "is_valid": False,
                    "type": "http_error",
                    "debug_message": str(e),
                    "message": f"HTTP {e.response.status_code}: {e.response.reason}"
                }

    def validate_dashboard(self, dashboard_json: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate dashboard JSON via DevRev API.

        Args:
            dashboard_json: Complete dashboard JSON dictionary

        Returns:
            Validation result:
            - is_valid (bool): Whether dashboard is valid
            - type (str): Error type if invalid
            - field_name (str): Field name if invalid
            - debug_message (str): Error details if invalid

        Raises:
            requests.HTTPError: If API call fails
        """
        url = f"{self.endpoint}/internal/dashboards.create.validate"

        # Wrap payload in {"dashboard": {...}} format expected by API
        wrapped = {"dashboard": dashboard_json}

        try:
            result = self._make_request("POST", url, wrapped)
            # If no error, validation passed
            return {"is_valid": True}
        except requests.HTTPError as e:
            # Parse error response
            try:
                error_data = e.response.json()
                return {
                    "is_valid": False,
                    "type": error_data.get('type', 'unknown'),
                    "field_name": error_data.get('field_name'),
                    "debug_message": error_data.get('debug_message', str(e)),
                    "message": error_data.get('message', 'Validation failed')
                }
            except Exception:
                return {
                    "is_valid": False,
                    "type": "http_error",
                    "debug_message": str(e),
                    "message": f"HTTP {e.response.status_code}: {e.response.reason}"
                }

    def list_dashboards(self, limit: int = 100) -> Dict[str, Any]:
        """
        List dashboards from DevRev platform.

        Args:
            limit: Maximum number of dashboards to return

        Returns:
            Dictionary with 'dashboards' array

        Raises:
            requests.HTTPError: If API call fails
        """
        url = f"{self.endpoint}/internal/dashboards.list"
        response = self._make_request("POST", url, {"limit": limit})
        return response

    def get_dashboard(self, dashboard_id: str) -> Dict[str, Any]:
        """
        Get dashboard details from DevRev platform.

        Args:
            dashboard_id: Dashboard DON ID (full or short)

        Returns:
            Dictionary with 'dashboard' object

        Raises:
            requests.HTTPError: If API call fails
        """
        url = f"{self.endpoint}/internal/dashboards.get"
        response = self._make_request("POST", url, {"id": dashboard_id})
        return response

    def get_widget(self, widget_id: str) -> Dict[str, Any]:
        """
        Get widget details from DevRev platform.

        Args:
            widget_id: Widget DON ID (full or short)

        Returns:
            Dictionary with 'widget' object

        Raises:
            requests.HTTPError: If API call fails
        """
        url = f"{self.endpoint}/internal/widgets.get"
        response = self._make_request("POST", url, {"id": widget_id})
        return response
