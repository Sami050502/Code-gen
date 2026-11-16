"""Debug logger for widget validation.

Appends structured JSONL logs to workspace/logs/validation-errors.jsonl for debugging and audit trail.
Each validation run appends one JSON line to the log file.

Includes validation loop detection to identify oscillating errors.
"""

import json
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from lib.core.models import ValidationResult, ValidationError


class ValidationLoopDetector:
    """Detects validation loops where the same errors keep repeating."""

    def __init__(self, log_file: Path, lookback_minutes: int = 30, min_occurrences: int = 3):
        """
        Initialize loop detector.

        Args:
            log_file: Path to validation-errors.jsonl
            lookback_minutes: How far back to look for patterns
            min_occurrences: Minimum occurrences to consider a loop
        """
        self.log_file = log_file
        self.lookback_minutes = lookback_minutes
        self.min_occurrences = min_occurrences

    def detect_loop(self, widget_file: str, current_errors: List[Dict]) -> Optional[Dict]:
        """
        Check if current errors match a repeating pattern.

        Args:
            widget_file: Path to widget being validated
            current_errors: List of current error dicts

        Returns:
            Dict with loop info if detected, None otherwise
        """
        if not self.log_file.exists():
            return None

        try:
            # Get current error signature
            current_sig = self._error_signature(current_errors)
            if not current_sig:
                return None

            # Read recent entries for this widget
            cutoff = datetime.utcnow() - timedelta(minutes=self.lookback_minutes)
            recent_sigs = []

            with open(self.log_file, 'r') as f:
                for line in f:
                    if not line.strip():
                        continue
                    try:
                        entry = json.loads(line)
                        # Check if same widget and within time window
                        if entry.get('widget_file', '').endswith(widget_file.split('/')[-1]):
                            timestamp = datetime.fromisoformat(entry['timestamp'].rstrip('Z'))
                            if timestamp >= cutoff:
                                # Extract error signature from this entry
                                errors = []
                                for stage in entry.get('stages', []):
                                    errors.extend(stage.get('errors', []))
                                sig = self._error_signature(errors)
                                if sig:
                                    recent_sigs.append(sig)
                    except (json.JSONDecodeError, KeyError, ValueError):
                        continue

            # Check for oscillation pattern (A -> B -> A -> B)
            if len(recent_sigs) >= 2:
                unique_sigs = list(dict.fromkeys(recent_sigs[-6:]))  # Last 6 entries
                if len(unique_sigs) == 2 and len(recent_sigs) >= 4:
                    # Oscillating between two error states
                    return {
                        "type": "OSCILLATING_ERRORS",
                        "message": "Validation is oscillating between two error states",
                        "suggestion": "Local validation and API may have conflicting requirements. Check schema alignment.",
                        "error_states": unique_sigs,
                        "occurrences": len(recent_sigs)
                    }

            # Check for repeating same error
            if recent_sigs.count(current_sig) >= self.min_occurrences:
                return {
                    "type": "REPEATED_ERROR",
                    "message": f"Same error has occurred {recent_sigs.count(current_sig)} times",
                    "suggestion": "This error is not being fixed. Check if the fix is being applied correctly.",
                    "error_signature": current_sig,
                    "occurrences": recent_sigs.count(current_sig)
                }

            return None

        except Exception:
            return None

    def _error_signature(self, errors: List[Dict]) -> str:
        """Create a signature string from errors for comparison."""
        if not errors:
            return ""
        # Sort by rule_id and field_path for consistent comparison
        sorted_errors = sorted(errors, key=lambda e: (e.get('rule_id', ''), e.get('field_path', '')))
        sig_parts = [f"{e.get('rule_id')}:{e.get('field_path', '')}" for e in sorted_errors]
        return "|".join(sig_parts)


class DebugLogger:
    """Debug logger that appends validation details to a single JSONL log file."""

    def __init__(self, workspace_path: Path, enabled: bool = True):
        """
        Initialize debug logger.

        Args:
            workspace_path: Path to workspace root
            enabled: Whether logging is enabled
        """
        self.workspace_path = Path(workspace_path)
        self.enabled = enabled
        self.log_dir = self.workspace_path / "logs"
        self.log_file = None
        self.log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "widget_file": None,
            "validation_mode": None,
            "stages": [],
            "final_result": None,
            "total_duration_ms": None,
            "environment": {}
        }
        self.start_time = time.time()

        # Create logs directory if it doesn't exist
        if self.enabled:
            try:
                self.log_dir.mkdir(parents=True, exist_ok=True)
                # Use fixed filename for JSONL append-only logging
                self.log_file = self.log_dir / "validation-errors.jsonl"

                # Verify directory is writable
                if not os.access(self.log_dir, os.W_OK):
                    raise PermissionError(f"Cannot write to {self.log_dir}")

            except Exception as e:
                # Disable and report to stderr
                self.enabled = False
                print(f"Warning: Could not initialize debug logger: {e}", file=sys.stderr, flush=True)

    def log_validation_start(self, widget_path: str, mode: str):
        """
        Log validation start.

        Args:
            widget_path: Path to widget file being validated
            mode: Validation mode ("skip_api" or "full_with_api")
        """
        if not self.enabled:
            return

        try:
            self.log_data["widget_file"] = widget_path
            self.log_data["validation_mode"] = mode
            self.log_data["environment"]["skip_api"] = (mode == "skip_api")
            self.log_data["environment"]["workspace_path"] = str(self.workspace_path)
        except Exception:
            pass  # Don't crash validation if logging fails

    def log_stage_result(self, stage: str, result: ValidationResult):
        """
        Log stage result.

        Args:
            stage: Stage name ("structure", "semantic", "api")
            result: ValidationResult object
        """
        if not self.enabled:
            return

        try:
            # Determine status
            if not result.valid:
                status = "failed"
            elif result.warnings:
                status = "passed_with_warnings"
            else:
                status = "passed"

            stage_data = {
                "stage": stage,
                "status": status,
                "duration_ms": 0,  # Will be calculated if needed
                "errors": [self._error_to_dict(e) for e in result.errors],
                "warnings": [self._error_to_dict(w) for w in result.warnings]
            }

            self.log_data["stages"].append(stage_data)
        except Exception:
            pass  # Don't crash validation if logging fails

    def log_exception(self, exception: Exception, context: str):
        """
        Log exception.

        Args:
            exception: Exception object
            context: Context where exception occurred
        """
        if not self.enabled:
            return

        try:
            # Add exception to current stage or create new stage
            exception_data = {
                "stage": context,
                "status": "exception",
                "duration_ms": 0,
                "errors": [{
                    "rule_id": "EXCEPTION",
                    "severity": "error",
                    "field_path": context,
                    "message": str(exception),
                    "suggestion": "Check stack trace and fix underlying issue"
                }],
                "warnings": []
            }
            self.log_data["stages"].append(exception_data)
        except Exception:
            pass  # Don't crash validation if logging fails

    def log_validation_end(self, total_duration: float, final_result: bool):
        """
        Log validation end and write log file.

        Args:
            total_duration: Total validation duration in seconds
            final_result: Whether validation passed overall
        """
        if not self.enabled or not self.log_file:
            return

        try:
            self.log_data["final_result"] = "valid" if final_result else "invalid"
            self.log_data["total_duration_ms"] = int(total_duration * 1000)

            # Append as single-line JSON to .jsonl file (JSONL format)
            with open(self.log_file, 'a') as f:
                json.dump(self.log_data, f, separators=(',', ':'))
                f.write('\n')
                f.flush()  # Ensure immediate write for concurrent access
        except Exception:
            pass  # Don't crash validation if logging fails

    def rotate_logs(self, max_size_mb: int = 50, max_files: int = 5):
        """
        Rotate log file when it exceeds max_size_mb.
        Keeps up to max_files rotated copies (e.g., validation-errors.jsonl.1, .2, etc.)

        Args:
            max_size_mb: Maximum size in MB before rotation (default 50)
            max_files: Maximum number of rotated files to keep (default 5)
        """
        if not self.enabled or not self.log_file or not self.log_file.exists():
            return

        try:
            # Allow environment variables to override defaults
            max_size_mb = int(os.environ.get('VALIDATION_LOG_MAX_SIZE_MB', max_size_mb))
            max_files = int(os.environ.get('VALIDATION_LOG_MAX_ROTATED', max_files))

            # Check file size
            file_size_mb = self.log_file.stat().st_size / (1024 * 1024)

            if file_size_mb > max_size_mb:
                # Rotate: .jsonl.4 → .jsonl.5, .jsonl.3 → .jsonl.4, etc.
                for i in range(max_files - 1, 0, -1):
                    old_file = Path(f"{self.log_file}.{i}")
                    new_file = Path(f"{self.log_file}.{i+1}")
                    if old_file.exists():
                        if new_file.exists():
                            new_file.unlink()
                        old_file.rename(new_file)

                # Rotate current file to .jsonl.1
                rotated = Path(f"{self.log_file}.1")
                if rotated.exists():
                    rotated.unlink()
                self.log_file.rename(rotated)

                # Fresh log file will be created on next append
        except Exception:
            pass  # Don't crash validation if log rotation fails

    def check_for_validation_loop(self, current_errors: List[ValidationError]) -> Optional[Dict]:
        """
        Check if current errors indicate a validation loop.

        Args:
            current_errors: List of current ValidationError objects

        Returns:
            Dict with loop info if detected, None otherwise
        """
        if not self.enabled or not self.log_file:
            return None

        try:
            detector = ValidationLoopDetector(self.log_file)
            error_dicts = [self._error_to_dict(e) for e in current_errors]
            return detector.detect_loop(
                self.log_data.get("widget_file", ""),
                error_dicts
            )
        except Exception:
            return None

    def _error_to_dict(self, error: ValidationError) -> Dict[str, Any]:
        """Convert ValidationError to dictionary."""
        return {
            "rule_id": error.rule_id,
            "severity": error.severity,
            "field_path": error.field_path,
            "message": error.message,
            "suggestion": error.suggestion
        }
