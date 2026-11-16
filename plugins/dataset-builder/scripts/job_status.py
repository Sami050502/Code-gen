#!/usr/bin/env python3
"""
Job status checker with polling support.

Usage:
    # Check status once
    python job_status.py <job_status_id>

    # Poll until completion (default: 5 second intervals, 10 minute timeout)
    python job_status.py <job_status_id> --poll

    # Custom polling interval and timeout
    python job_status.py <job_status_id> --poll --interval 10 --timeout 300
"""

import argparse
import json
import os
import sys
import time
from typing import Optional

try:
    import requests
except ImportError:
    print("Error: requests library not installed. Run: pip install requests", file=sys.stderr)
    sys.exit(1)

from pat_decoder import load_pat_from_env, get_environment_from_pat


def check_job_status(pat: str, job_status_id: str) -> dict:
    """
    Check the status of a job execution.

    Args:
        pat: DevRev PAT token
        job_status_id: The job status ID (don:core:...)

    Returns:
        Job status response dict
    """
    _, api_url = get_environment_from_pat(pat)

    url = f"{api_url}/internal/jobs.get"
    headers = {
        'Authorization': f'Bearer {pat}',
        'Content-Type': 'application/json',
    }

    response = requests.get(url, headers=headers, params={"id": job_status_id})
    response.raise_for_status()
    return response.json()


def get_status_summary(job_data: dict) -> dict:
    """Extract key status info from job response."""
    job = job_data.get("job", {})
    return {
        "status": job.get("status", "unknown"),
        "progress": job.get("progress", 0),
        "title": job.get("title", ""),
        "message": job.get("message", ""),
    }


def poll_job_status(pat: str, job_status_id: str, interval: int = 5, timeout: int = 600) -> dict:
    """
    Poll job status until completion or timeout.

    Args:
        pat: DevRev PAT token
        job_status_id: The job status ID
        interval: Seconds between polls
        timeout: Maximum seconds to wait

    Returns:
        Final job status response
    """
    start_time = time.time()
    last_progress = -1

    while True:
        elapsed = time.time() - start_time
        if elapsed > timeout:
            print(f"\nTimeout after {timeout} seconds", file=sys.stderr)
            sys.exit(1)

        try:
            result = check_job_status(pat, job_status_id)
            summary = get_status_summary(result)

            status = summary["status"]
            progress = summary["progress"]

            # Only print if progress changed
            if progress != last_progress:
                print(f"Status: {status} | Progress: {progress}%")
                last_progress = progress

            if status == "completed":
                print("\n✓ Job completed successfully!")
                return result
            elif status == "failed":
                print(f"\n✗ Job failed: {summary.get('message', 'Unknown error')}")
                return result
            elif status not in ("queued", "in_progress", "running"):
                print(f"\n? Unknown status: {status}")
                return result

            time.sleep(interval)

        except requests.exceptions.HTTPError as e:
            print(f"\nAPI error: {e}", file=sys.stderr)
            try:
                print(f"Details: {e.response.json()}", file=sys.stderr)
            except:
                pass
            sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Check DevRev job execution status",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Check status once
  python job_status.py "don:core:dvrv-us-1:devo/787:job/123"

  # Poll until completion
  python job_status.py "don:core:dvrv-us-1:devo/787:job/123" --poll

  # Custom polling interval (10 seconds)
  python job_status.py "don:core:dvrv-us-1:devo/787:job/123" --poll --interval 10
"""
    )

    parser.add_argument("job_status_id", help="Job status ID (don:core:...)")
    parser.add_argument("--poll", action="store_true", help="Poll until completion")
    parser.add_argument("--interval", type=int, default=5, help="Poll interval in seconds (default: 5)")
    parser.add_argument("--timeout", type=int, default=600, help="Timeout in seconds (default: 600)")
    parser.add_argument("--env-file", default=None, help="Path to .env file (auto-searches if not specified)")
    parser.add_argument("--json", action="store_true", help="Output raw JSON")

    args = parser.parse_args()

    try:
        pat = load_pat_from_env(args.env_file)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        print("Set DEVREV_PAT environment variable or create .env file", file=sys.stderr)
        sys.exit(1)

    try:
        if args.poll:
            result = poll_job_status(pat, args.job_status_id, args.interval, args.timeout)
        else:
            result = check_job_status(pat, args.job_status_id)
            summary = get_status_summary(result)
            print(f"Status: {summary['status']} | Progress: {summary['progress']}%")

        if args.json:
            print(json.dumps(result, indent=2))

    except requests.exceptions.HTTPError as e:
        error = {"error": str(e)}
        try:
            error["details"] = e.response.json()
        except:
            error["details"] = e.response.text
        print(json.dumps(error, indent=2), file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
