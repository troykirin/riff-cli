# Copyright 2024 NabiaTech
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Configuration loading from XDG Base Directory Specification

This module provides configuration loading from ~/.config/nabi/riff.toml
with educational comments that teach the XDG pattern. If the config file
doesn't exist, it's automatically created with sensible defaults and multi-line
comments explaining:
  - What XDG is and why it matters for portable software
  - Why configuration, data, and state are in separate directories
  - How to customize paths for your use case
  - Where backups are stored and how to access them

This is intentionally designed as an onboarding tool for the NabiOS
architecture pattern.
"""

from pathlib import Path
from typing import Optional, Dict, Any, List
import toml
import os
from dataclasses import dataclass, field


@dataclass
class QdrantEndpoint:
    """Represents a Qdrant endpoint with health and performance metadata"""
    name: str
    url: str
    priority: int
    is_primary: bool = False
    gpu_enabled: bool = False
    platform: str = "unknown"
    url_backup: Optional[str] = None
    health_timeout_ms: int = 2000
    description: str = ""


# Default educational TOML configuration with explanation
DEFAULT_CONFIG_TEMPLATE = """# Riff Configuration - XDG Base Directory Specification
#
# This configuration file teaches the XDG Base Directory Specification, a standard
# for organizing application data across Linux, macOS, and other Unix-like systems.
#
# ============================================================================
# WHAT IS XDG?
# ============================================================================
#
# XDG defines standard locations for different types of application data:
#
#   ~/.config/nabi/        <- Configuration files (what you're reading now)
#   ~/.local/share/nabi/   <- Application data (conversations, embeddings, backups)
#   ~/.local/state/nabi/   <- Runtime state (logs, caches, temporary indexes)
#   ~/.cache/nabi/         <- Temporary cache (can be deleted safely)
#
# Instead of everything living in ~/.riff or ~/.claude, this separation provides:
#
#   ✓ Portability: Move configs between machines easily
#   ✓ Backup Strategy: Only backup ~/.local/share, not temp files
#   ✓ Clean Organization: Find what you need by directory purpose
#   ✓ Federation Compatibility: NabiOS uses this pattern for all tools
#
# ============================================================================
# HOW TO CUSTOMIZE THESE PATHS
# ============================================================================
#
# Each section below controls where riff stores specific types of data.
# You can change any path, but we recommend keeping the XDG structure.
#
# Tips:
#   - Paths starting with ~ are expanded to your home directory
#   - Create parent directories before running riff if they don't exist
#   - Use absolute paths (e.g., /Volumes/backup/my-embeddings) for external drives
#   - Environment variables: RIFF_CONFIG, RIFF_DATA_DIR, RIFF_STATE_DIR, RIFF_CACHE_DIR
#
# ============================================================================
# CONFIGURATION SECTION (You Are Here)
# ============================================================================
#
# This file itself lives in ~/.config/nabi/riff.toml
# It contains all user preferences and optional feature toggles.
# Safe to edit and commit to version control (never contains secrets).
#

# ============================================================================
# PATHS: Where Each Type of Data Lives
# ============================================================================
#
[paths]

# Where to find your Claude conversations for analysis
# Default: ~/.claude/projects
#   - This is where claude-manager stores conversation JSONLs
#   - You can change this to analyze conversations from a different location
#   - Riff doesn't modify files here unless you run 'fix'
conversations = "~/.claude/projects"

# Where riff stores embeddings and semantic indexes
# Default: ~/.local/share/nabi/riff/embeddings (XDG data directory)
#   - This is your long-term semantic index
#   - Safe to delete and regenerate (will be slow)
#   - Good candidate for backup/synchronization
embeddings = "~/.local/share/nabi/riff/embeddings"

# Where riff stores conversation backups before fixing
# Default: ~/.local/share/nabi/riff/backups (XDG data directory)
#   - Riff automatically backs up conversations before repairing them
#   - Timestamped folders: 2025-11-10T143022-d58b28a9-5b9f-490b.jsonl
#   - Safe to clean up old backups manually
backups = "~/.local/share/nabi/riff/backups"

# Where riff stores temporary working files and caches
# Default: ~/.cache/nabi/riff (XDG cache directory)
#   - Temporary files that can be deleted without harm
#   - Can be on fast SSD or even /tmp for faster indexing
#   - Riff cleans this up periodically
cache = "~/.cache/nabi/riff"

# Where riff stores runtime state and hot-reloadable indexes
# Default: ~/.local/state/nabi/riff (XDG state directory)
#   - Hot-reloadable backup index (updates as backups are created)
#   - Last-indexed timestamps for watch operations
#   - Can be cleared without losing data, will be regenerated
state = "~/.local/state/nabi/riff"

# ============================================================================
# MODELS: Embedding and AI Configuration
# ============================================================================
#
[models]

# Which embedding model to use for semantic search
# Default: "BAAI/bge-small-en-v1.5" (384-dimensional, 33 MB, fast)
# Alternative: "BAAI/bge-base-en-v1.5" (768-dimensional, 139 MB, better quality)
embedding = "BAAI/bge-small-en-v1.5"

# Dimensionality of the embedding vectors
# This should match your embedding model:
#   - bge-small-en-v1.5 = 384 dimensions
#   - bge-base-en-v1.5 = 768 dimensions
embedding_dimension = 384

# ============================================================================
# QDRANT: Vector Database Configuration
# ============================================================================
#
# Qdrant is an optional vector database for semantic search.
# If Qdrant is not running, search features will gracefully degrade with a helpful message.
#
[qdrant]

# Qdrant HTTP endpoint
# Default: "http://localhost:6333"
# Docker: docker run -p 6333:6333 qdrant/qdrant
endpoint = "http://localhost:6333"

# Collection name for storing conversation embeddings
collection = "claude_sessions"

# ============================================================================
# VENV: Python Virtual Environment
# ============================================================================
#
[venv]

# Where riff stores its Python virtual environment
# Default: "~/.nabi/venvs/riff"
# This is managed automatically by the nabi tool ecosystem
location = "~/.nabi/venvs/riff"

# ============================================================================
# OPTIONAL FEATURES: Advanced Configuration
# ============================================================================
#
[features]

# Enable semantic search (requires Qdrant and embeddings)
# Default: false (search feature is optional)
search_enabled = false

# Enable SurrealDB integration for immutable event logging
# Default: false (SurrealDB integration is experimental)
surrealdb_enabled = false

# ============================================================================
# WHY THIS STRUCTURE MATTERS FOR NABITECH
# ============================================================================
#
# The Nabia system (~/nabia/) uses this XDG pattern for ALL tools, which enables:
#
#   1. PORTABLE CONFIGURATIONS
#      All tools use ~/.config/nabi/{tool}/ → easy to sync across machines
#
#   2. SMART BACKUPS
#      Backup only ~/.local/share/nabi/ → protects all application data
#      Ignore ~/.cache/ and ~/.local/state/ → they're temporary
#
#   3. FEDERATION DISCOVERY
#      The nabi CLI finds all registered tools by scanning ~/.config/nabi/
#      New tools automatically integrate with the ecosystem
#
#   4. HOT-RELOAD COORDINATION
#      The ~/.local/state/ files enable inter-process communication
#      Tools can coordinate without restarting each other
#
# By learning this pattern through riff, you're preparing for the
# full NabiOS experience, where dozens of coordinated tools share
# this single architectural pattern.
#
# ============================================================================
"""


class RiffConfig:
    """Riff configuration from XDG Base Directory Specification

    This class provides optional configuration loading with auto-creation of
    sensible defaults. If the config file doesn't exist, it's created with
    educational comments explaining the XDG pattern.
    """

    def __init__(self, config_path: Optional[Path] = None):
        if config_path is None:
            # Support environment variable override
            config_path_env = os.environ.get("RIFF_CONFIG")
            if config_path_env:
                config_path = Path(config_path_env).expanduser()
            else:
                config_path = Path.home() / ".config/nabi/riff.toml"

        self._config_path = config_path

        # Auto-create config with defaults if it doesn't exist
        if not config_path.exists():
            self._create_default_config(config_path)

        # Load the configuration
        try:
            self._config = toml.load(config_path)
        except Exception as e:
            # Fallback to empty config if parsing fails
            print(f"Warning: Failed to parse {config_path}: {e}")
            self._config = {}

    @staticmethod
    def _create_default_config(config_path: Path) -> None:
        """Create default config file with educational comments if it doesn't exist"""
        # Ensure parent directories exist
        config_path.parent.mkdir(parents=True, exist_ok=True)

        # Write the educational template
        with open(config_path, "w", encoding="utf-8") as f:
            f.write(DEFAULT_CONFIG_TEMPLATE)

        # Also ensure XDG directories exist
        data_dir = Path.home() / ".local/share/nabi/riff"
        state_dir = Path.home() / ".local/state/nabi/riff"
        cache_dir = Path.home() / ".cache/nabi/riff"

        for d in [data_dir, state_dir, cache_dir]:
            d.mkdir(parents=True, exist_ok=True)

        print(f"[✓] Created XDG configuration at {config_path}")
        print(f"[✓] Created XDG directories:")
        print(f"    - {data_dir}")
        print(f"    - {state_dir}")
        print(f"    - {cache_dir}")
        print(f"\n[💡] Open {config_path} to understand the XDG architecture\n")

    @property
    def embedding_model(self) -> str:
        """Get configured embedding model"""
        return self._config.get("models", {}).get(
            "embedding",
            "BAAI/bge-small-en-v1.5"  # Fallback default
        )

    @property
    def embedding_dimension(self) -> int:
        """Get embedding vector dimension"""
        return self._config.get("models", {}).get("embedding_dimension", 384)

    @property
    def qdrant_endpoint(self) -> str:
        """Get Qdrant endpoint from config"""
        return self._config.get("qdrant", {}).get(
            "endpoint",
            "http://localhost:6333"
        )

    @property
    def qdrant_collection(self) -> str:
        """Get Qdrant collection name"""
        return self._config.get("qdrant", {}).get(
            "collection",
            "claude_sessions"
        )

    @property
    def paths(self) -> Dict[str, Path]:
        """Get XDG-compliant paths from config with environment variable overrides"""
        paths_config = self._config.get("paths", {})

        # Allow environment variable overrides for flexibility
        conversations = os.environ.get(
            "RIFF_CONVERSATIONS_DIR",
            paths_config.get("conversations", "~/.claude/projects")
        )
        embeddings = os.environ.get(
            "RIFF_EMBEDDINGS_DIR",
            paths_config.get("embeddings", "~/.local/share/nabi/riff/embeddings")
        )
        backups = os.environ.get(
            "RIFF_BACKUPS_DIR",
            paths_config.get("backups", "~/.local/share/nabi/riff/backups")
        )
        cache = os.environ.get(
            "RIFF_CACHE_DIR",
            paths_config.get("cache", "~/.cache/nabi/riff")
        )
        state = os.environ.get(
            "RIFF_STATE_DIR",
            paths_config.get("state", "~/.local/state/nabi/riff")
        )

        return {
            "conversations": Path(conversations).expanduser(),
            "embeddings": Path(embeddings).expanduser(),
            "backups": Path(backups).expanduser(),
            "cache": Path(cache).expanduser(),
            "state": Path(state).expanduser(),
        }

    @property
    def venv_location(self) -> Path:
        """Get venv location from config"""
        venv_config = self._config.get("venv", {})
        return Path(
            venv_config.get("location", "~/.nabi/venvs/riff")
        ).expanduser()

    @property
    def surrealdb_endpoint(self) -> str:
        """Get SurrealDB endpoint from config"""
        return self._config.get("surrealdb", {}).get(
            "endpoint",
            "http://localhost:8284"  # Federation default
        )

    @property
    def surrealdb_namespace(self) -> str:
        """Get SurrealDB namespace from config"""
        return self._config.get("surrealdb", {}).get(
            "namespace",
            "memory"  # Federation memory namespace
        )

    @property
    def surrealdb_database(self) -> str:
        """Get SurrealDB database from config"""
        return self._config.get("surrealdb", {}).get(
            "database",
            "riff"
        )

    @property
    def surrealdb_username(self) -> str:
        """Get SurrealDB username from config"""
        return self._config.get("surrealdb", {}).get(
            "username",
            "root"
        )

    @property
    def surrealdb_password(self) -> str:
        """Get SurrealDB password from config"""
        return self._config.get("surrealdb", {}).get(
            "password",
            "federation-root-pass"
        )

    @property
    def surrealdb_enabled(self) -> bool:
        """Check if SurrealDB integration is enabled"""
        return self._config.get("features", {}).get(
            "surrealdb_enabled",
            False
        )

    @property
    def qdrant_routing_config_path(self) -> Optional[Path]:
        """Get path to Qdrant routing config if it exists"""
        # Check environment variable first
        routing_path_env = os.environ.get("RIFF_QDRANT_ROUTING_CONFIG")
        if routing_path_env:
            path = Path(routing_path_env).expanduser()
            if path.exists():
                return path

        # Check default location
        default_path = Path.home() / ".config/nabi/riff-qdrant-routing.toml"
        if default_path.exists():
            return default_path

        return None

    def load_routing_config(self) -> Optional[Dict[str, Any]]:
        """Load the Qdrant routing configuration file"""
        routing_path = self.qdrant_routing_config_path
        if routing_path is None:
            return None

        try:
            return toml.load(routing_path)
        except Exception as e:
            print(f"Warning: Failed to parse routing config {routing_path}: {e}")
            return None

    def get_qdrant_endpoints(self) -> List[QdrantEndpoint]:
        """Get list of Qdrant endpoints from routing config, sorted by priority"""
        routing_config = self.load_routing_config()
        if routing_config is None:
            # Fallback to single endpoint from qdrant config section
            return [QdrantEndpoint(
                name="default",
                url=self.qdrant_endpoint,
                priority=1,
                is_primary=True,
                platform="local"
            )]

        endpoints = []
        for ep_config in routing_config.get("endpoints", []):
            # Handle nested health config
            health_config = ep_config.get("health", {})
            timeout_ms = health_config.get("timeout_ms", 2000)

            endpoint = QdrantEndpoint(
                name=ep_config.get("name", "unknown"),
                url=ep_config.get("url", "http://localhost:6333"),
                priority=ep_config.get("priority", 99),
                is_primary=ep_config.get("is_primary", False),
                gpu_enabled=ep_config.get("gpu_enabled", False),
                platform=ep_config.get("platform", "unknown"),
                url_backup=ep_config.get("url_backup"),
                health_timeout_ms=timeout_ms,
                description=ep_config.get("description", "")
            )
            endpoints.append(endpoint)

        # Sort by priority (lower = higher priority)
        endpoints.sort(key=lambda e: e.priority)
        return endpoints

    def get_primary_qdrant_url(self) -> str:
        """Get the primary (highest priority) Qdrant URL from routing config"""
        endpoints = self.get_qdrant_endpoints()
        if endpoints:
            return endpoints[0].url
        return self.qdrant_endpoint

    @property
    def routing_enabled(self) -> bool:
        """Check if routing config exists and should be used"""
        return self.qdrant_routing_config_path is not None

    def get(self, key: str, default: Any = None) -> Any:
        """Get arbitrary config value"""
        keys = key.split(".")
        value = self._config

        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
                if value is None:
                    return default
            else:
                return default

        return value if value is not None else default


# Global config instance (lazy-loaded)
_config: Optional[RiffConfig] = None


def get_config() -> RiffConfig:
    """Get global config instance (singleton)"""
    global _config
    if _config is None:
        _config = RiffConfig()
    return _config


def reload_config():
    """Force reload configuration from disk"""
    global _config
    _config = None
    return get_config()


# Convenience functions for backward compatibility
def get_embedding_model() -> str:
    """Get configured embedding model"""
    return get_config().embedding_model


def get_qdrant_endpoint() -> str:
    """Get Qdrant endpoint from config"""
    return get_config().qdrant_endpoint


def get_paths() -> Dict[str, Path]:
    """Get XDG-compliant paths from config"""
    return get_config().paths


def get_qdrant_endpoints() -> List[QdrantEndpoint]:
    """Get list of Qdrant endpoints from routing config"""
    return get_config().get_qdrant_endpoints()


def get_primary_qdrant_url() -> str:
    """Get the primary Qdrant URL (respects routing config if present)"""
    return get_config().get_primary_qdrant_url()
