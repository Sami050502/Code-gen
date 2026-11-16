"""Schema caching for improved performance."""

import time
from pathlib import Path
from typing import Optional, Dict, Any

from .parser import MosaicSchemaParser


class SchemaCache:
    """
    Caches parsed schemas to avoid repeated parsing.
    Monitors schema file for changes and invalidates cache when needed.
    """

    def __init__(self, ttl: int = 3600):
        """
        Initialize cache.

        Args:
            ttl: Time-to-live in seconds (default: 1 hour)
        """
        self.ttl = ttl
        self._cache: Dict[str, Any] = {}
        self._parser: Optional[MosaicSchemaParser] = None
        self._schema_path: Optional[Path] = None
        self._last_mtime: Optional[float] = None
        self._last_check: float = 0

    def get_parser(self, schema_path: Optional[Path] = None) -> MosaicSchemaParser:
        """
        Get cached parser or create new one.

        Args:
            schema_path: Path to schema file

        Returns:
            MosaicSchemaParser instance
        """
        current_time = time.time()

        # Initialize if needed
        if self._parser is None:
            self._parser = MosaicSchemaParser(schema_path)
            self._schema_path = self._parser.schema_path
            if self._schema_path.exists():
                self._last_mtime = self._schema_path.stat().st_mtime
            self._last_check = current_time
            return self._parser

        # Check if cache expired or file changed
        if current_time - self._last_check > 5:  # Check every 5 seconds
            self._last_check = current_time

            if self._schema_path and self._schema_path.exists():
                current_mtime = self._schema_path.stat().st_mtime
                if current_mtime != self._last_mtime:
                    # File changed, reload
                    self._parser.reload()
                    self._last_mtime = current_mtime
                    self._cache.clear()

        return self._parser

    def clear(self):
        """Clear cache."""
        self._cache.clear()
        self._parser = None
        self._last_mtime = None
        self._last_check = 0


# Global cache instance
_global_cache = SchemaCache()


def get_cached_parser(schema_path: Optional[Path] = None) -> MosaicSchemaParser:
    """
    Get cached parser instance.

    Args:
        schema_path: Path to schema file

    Returns:
        Cached MosaicSchemaParser instance
    """
    return _global_cache.get_parser(schema_path)


def clear_cache():
    """Clear global cache."""
    _global_cache.clear()
