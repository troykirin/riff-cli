"""
Manifest adapter for riff-cli.

This module provides a pluggable interface for checking if reindex is needed.
When your system-level manifest system is ready, this adapter can be updated
to use that instead, without changing riff-cli's search logic.

Philosophy:
- Keep logic simple and modular
- Support future system-wide manifest integration
- Never duplicate logic from the source of truth
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Dict, Tuple
import hashlib
import json
from datetime import datetime


class ManifestAdapter(ABC):
    """Abstract base for manifest checking strategies."""

    @abstractmethod
    def needs_reindex(self) -> bool:
        """Check if Claude projects directory has changed."""
        pass

    @abstractmethod
    def get_changes_summary(self) -> str:
        """Get human-readable summary of what changed."""
        pass

    @abstractmethod
    def save_manifest(self) -> None:
        """Save/update the manifest after reindexing."""
        pass


class LocalManifestAdapter(ManifestAdapter):
    """
    Lightweight local manifest adapter using SHA256 hashing.

    Stores manifest in ~/.local/state/nabi/riff/projects_manifest.json

    TODO: When the system-level manifest is ready, create:
    - SystemManifestAdapter (queries ~/.nabi/state/manifest.json)
    - HybridManifestAdapter (tries system first, falls back to local)
    """

    def __init__(self):
        self.projects_dir = Path.home() / ".claude" / "projects"
        self.manifest_cache_dir = Path.home() / ".local" / "state" / "nabi" / "riff"
        self.manifest_cache_file = self.manifest_cache_dir / "projects_manifest.json"
        self.manifest_cache_dir.mkdir(parents=True, exist_ok=True)

        self._current_manifest: Dict[str, str] = {}
        self._last_manifest: Dict[str, str] = {}
        self._changes_summary: str = ""

    @staticmethod
    def _sha256_file(file_path: Path) -> str:
        """Calculate SHA256 hash of a file."""
        sha256 = hashlib.sha256()
        try:
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(8192), b''):
                    sha256.update(chunk)
            return sha256.hexdigest()
        except Exception:
            return ""

    def _generate_current_manifest(self) -> Dict[str, str]:
        """Generate SHA256 manifest of all .jsonl files."""
        manifest = {}
        if self.projects_dir.exists():
            for jsonl_file in self.projects_dir.rglob("*.jsonl"):
                try:
                    rel_path = str(jsonl_file.relative_to(self.projects_dir))
                    manifest[rel_path] = self._sha256_file(jsonl_file)
                except Exception:
                    pass
        return manifest

    def _load_last_manifest(self) -> Dict[str, str]:
        """Load the previously saved manifest."""
        if not self.manifest_cache_file.exists():
            return {}

        try:
            with open(self.manifest_cache_file) as f:
                data = json.load(f)
                return data.get("manifest", {})
        except Exception:
            return {}

    def needs_reindex(self) -> bool:
        """Check if projects directory has changed since last index."""
        self._current_manifest = self._generate_current_manifest()
        self._last_manifest = self._load_last_manifest()

        # First time
        if not self._last_manifest:
            self._changes_summary = f"First indexing ({len(self._current_manifest)} sessions)"
            return True

        # Check for changes
        current_files = set(self._current_manifest.keys())
        last_files = set(self._last_manifest.keys())

        added = current_files - last_files
        removed = last_files - current_files
        modified = [f for f in current_files & last_files
                   if self._current_manifest[f] != self._last_manifest[f]]

        if added or removed or modified:
            summary_parts = []
            if added:
                summary_parts.append(f"+{len(added)}")
            if removed:
                summary_parts.append(f"-{len(removed)}")
            if modified:
                summary_parts.append(f"~{len(modified)}")
            self._changes_summary = ", ".join(summary_parts) + " sessions changed"
            return True

        return False

    def get_changes_summary(self) -> str:
        """Get human-readable summary of what changed."""
        return self._changes_summary

    def save_manifest(self) -> None:
        """Save current manifest for comparison on next run."""
        try:
            data = {
                "manifest": self._current_manifest,
                "timestamp": datetime.utcnow().isoformat(),
                "file_count": len(self._current_manifest)
            }
            with open(self.manifest_cache_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass

    def validate_index_integrity(self, indexed_sessions: list) -> bool:
        """
        Validate that indexed sessions actually exist on disk.

        Detects when Qdrant has stale data pointing to files that no longer exist.
        This catches scenarios where Claude Code moved/deleted sessions but
        Qdrant still has the old index entries.

        Memory Substrate Integration:
        - Logs validation failures to memory:item stream
        - Phase 3A can track staleness trends over time
        - Enables root cause analysis of index divergence

        Args:
            indexed_sessions: List of session file paths from Qdrant index

        Returns:
            True if all indexed sessions exist, False if index is stale
        """
        if not indexed_sessions:
            return True

        missing_count = 0
        for session_path in indexed_sessions:
            session_file = Path(session_path)
            if not session_file.exists():
                missing_count += 1

        # If >10% of indexed sessions are missing, index is stale
        if missing_count > 0:
            stale_percentage = (missing_count / len(indexed_sessions)) * 100
            self._changes_summary = f"Index stale: {missing_count}/{len(indexed_sessions)} sessions missing ({stale_percentage:.1f}%)"

            # Log validation failure to memory substrate
            try:
                from .memory_producer import get_memory_producer
                memory = get_memory_producer()
                memory.log_validation_failed(
                    missing_count=missing_count,
                    total_indexed=len(indexed_sessions),
                    stale_percentage=stale_percentage
                )
            except Exception:
                # Graceful degradation: If memory logging fails, validation still works
                pass

            return False

        return True


def get_manifest_adapter() -> ManifestAdapter:
    """
    Factory function to get the appropriate manifest adapter.

    Future: This can be updated to:
    - Try system-level manifest first
    - Fall back to local manifest
    - Support hybrid/concurrent checking
    """
    return LocalManifestAdapter()
