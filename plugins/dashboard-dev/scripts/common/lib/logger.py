"""
Centralized logging for dashboard-dev scripts.

Usage:
    from logger import info, debug, warn, error, success, progress, result

    # User-facing output (always shown)
    success("Widget created successfully")
    error("Failed to connect")
    result("Summary: 6 datasets downloaded")

    # Progress output (hidden by default)
    progress("Downloading schema...")
    info("Processing 10 items")

    # Debug output (hidden by default)
    debug(f"API response: {response}")

Control verbosity:
    --verbose flag in CLI scripts
    DASHBOARD_DEV_VERBOSE=1 environment variable
    --quiet flag or DASHBOARD_DEV_QUIET=1 for minimal output
"""

import sys
import os

# Verbosity levels
QUIET = 0      # Errors only
NORMAL = 1     # Errors + success + summary
VERBOSE = 2    # All output

_verbosity = NORMAL


def set_verbosity(level: int):
    """Set global verbosity level."""
    global _verbosity
    _verbosity = level


def get_verbosity() -> int:
    """Get current verbosity level."""
    return _verbosity


def is_verbose() -> bool:
    """Check if verbose mode is enabled."""
    return _verbosity >= VERBOSE


def init_from_env():
    """Initialize verbosity from environment."""
    global _verbosity
    if os.environ.get('DASHBOARD_DEV_VERBOSE', '').lower() in ('1', 'true', 'yes'):
        _verbosity = VERBOSE
    elif os.environ.get('DASHBOARD_DEV_QUIET', '').lower() in ('1', 'true', 'yes'):
        _verbosity = QUIET


# Initialize from environment on import
init_from_env()


# === Output Functions ===

def error(msg: str):
    """Error message (always shown)."""
    print(f"❌ {msg}", file=sys.stderr)


def warn(msg: str):
    """Warning message (always shown)."""
    print(f"⚠️  {msg}", file=sys.stderr)


def success(msg: str):
    """Success message (always shown)."""
    print(f"✅ {msg}")


def result(msg: str):
    """Result/summary output (always shown)."""
    print(msg)


def info(msg: str):
    """Info message (verbose only)."""
    if _verbosity >= VERBOSE:
        print(msg)


def progress(msg: str, end: str = '\n'):
    """Progress message (verbose only)."""
    if _verbosity >= VERBOSE:
        print(msg, end=end, file=sys.stderr)


def progress_item(msg: str, end: str = '\n'):
    """Progress item with indentation (verbose only)."""
    if _verbosity >= VERBOSE:
        print(f"  {msg}", end=end, file=sys.stderr)


def debug(msg: str):
    """Debug message (verbose only)."""
    if _verbosity >= VERBOSE:
        print(f"[DEBUG] {msg}", file=sys.stderr)


def header(title: str):
    """Section header (verbose only)."""
    if _verbosity >= VERBOSE:
        print(f"\n{'='*60}")
        print(title)
        print('='*60)


def subheader(title: str):
    """Subsection header (verbose only)."""
    if _verbosity >= VERBOSE:
        print(f"\n{title}")
        print('-'*60)


def divider():
    """Divider line (verbose only)."""
    if _verbosity >= VERBOSE:
        print('-'*60)


def newline():
    """Print newline (verbose only)."""
    if _verbosity >= VERBOSE:
        print()


# === Helper for argparse ===

def add_verbosity_args(parser):
    """Add --verbose and --quiet arguments to an argparse parser."""
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Show detailed progress output'
    )
    parser.add_argument(
        '--quiet', '-q',
        action='store_true',
        help='JSON output only (suppresses colored terminal output; also via DASHBOARD_DEV_QUIET=1)'
    )


def apply_verbosity_args(args):
    """Apply verbosity settings from parsed args."""
    if getattr(args, 'verbose', False):
        set_verbosity(VERBOSE)
    elif getattr(args, 'quiet', False):
        set_verbosity(QUIET)
