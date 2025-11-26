"""Qdrant Router: Intelligent endpoint selection with health checks and failover

This module implements the federated GPU architecture designed for:
- Primary: WSL GPU Qdrant (NVIDIA 5070Ti via Tailscale MagicDNS)
- Fallback: macOS CPU Qdrant (localhost)
- Strategy: Automatic failover with health checks

The router reads from ~/.config/nabi/riff-qdrant-routing.toml and provides:
- Health-aware endpoint selection
- Automatic failover on connection errors
- Backup URL support for MagicDNS failures
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, Dict, List
from enum import Enum
import urllib.request
import urllib.error


class EndpointStatus(Enum):
    """Health status of a Qdrant endpoint"""
    UNKNOWN = "unknown"
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"  # Backup URL in use


@dataclass
class EndpointHealth:
    """Tracks health state for a single endpoint"""
    status: EndpointStatus = EndpointStatus.UNKNOWN
    last_check: Optional[datetime] = None
    last_success: Optional[datetime] = None
    consecutive_failures: int = 0
    last_latency_ms: Optional[float] = None
    using_backup_url: bool = False


@dataclass
class QdrantEndpoint:
    """Endpoint configuration from routing config"""
    name: str
    url: str
    priority: int
    is_primary: bool = False
    gpu_enabled: bool = False
    platform: str = "unknown"
    url_backup: Optional[str] = None
    health_timeout_ms: int = 2000
    description: str = ""


class QdrantRouter:
    """Routes Qdrant requests to the best available endpoint

    Implements failover strategy:
    1. Try primary endpoint first
    2. If primary fails, try its backup URL (e.g., IP instead of MagicDNS)
    3. If both fail, fall back to secondary endpoints
    4. Periodically re-check primary to recover when available
    """

    def __init__(self, endpoints: Optional[List[QdrantEndpoint]] = None):
        """Initialize router with endpoints from config or provided list"""
        if endpoints is None:
            # Load from config
            from ..config import get_config
            config = get_config()
            config_endpoints = config.get_qdrant_endpoints()
            # Convert config endpoints to router endpoints
            self.endpoints = [
                QdrantEndpoint(
                    name=e.name,
                    url=e.url,
                    priority=e.priority,
                    is_primary=e.is_primary,
                    gpu_enabled=e.gpu_enabled,
                    platform=e.platform,
                    url_backup=e.url_backup,
                    health_timeout_ms=e.health_timeout_ms,
                    description=e.description
                ) for e in config_endpoints
            ]
        else:
            self.endpoints = endpoints

        # Track health state for each endpoint
        self._health: Dict[str, EndpointHealth] = {
            ep.name: EndpointHealth() for ep in self.endpoints
        }

        # Cache the current best endpoint
        self._current_endpoint: Optional[QdrantEndpoint] = None
        self._current_url: Optional[str] = None

        # Configuration
        self._health_check_interval = timedelta(seconds=30)
        self._failover_after_failures = 1

    def _check_endpoint_health(self, endpoint: QdrantEndpoint, use_backup: bool = False) -> bool:
        """Check if an endpoint is healthy by hitting its root URL"""
        url = endpoint.url_backup if use_backup and endpoint.url_backup else endpoint.url
        timeout_sec = endpoint.health_timeout_ms / 1000.0

        try:
            start = time.time()
            req = urllib.request.Request(url, method='GET')
            with urllib.request.urlopen(req, timeout=timeout_sec) as response:
                latency_ms = (time.time() - start) * 1000

                if response.status == 200:
                    health = self._health[endpoint.name]
                    health.status = EndpointStatus.DEGRADED if use_backup else EndpointStatus.HEALTHY
                    health.last_check = datetime.now()
                    health.last_success = datetime.now()
                    health.consecutive_failures = 0
                    health.last_latency_ms = latency_ms
                    health.using_backup_url = use_backup
                    return True

        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError):
            pass

        # Mark as unhealthy
        health = self._health[endpoint.name]
        health.consecutive_failures += 1
        health.last_check = datetime.now()

        if health.consecutive_failures >= self._failover_after_failures:
            health.status = EndpointStatus.UNHEALTHY

        return False

    def _needs_health_check(self, endpoint: QdrantEndpoint) -> bool:
        """Determine if endpoint needs a fresh health check"""
        health = self._health[endpoint.name]

        # Always check if never checked
        if health.last_check is None:
            return True

        # Check if interval has passed
        elapsed = datetime.now() - health.last_check
        return elapsed >= self._health_check_interval

    def get_best_url(self, force_check: bool = False) -> str:
        """Get the best available Qdrant URL

        Args:
            force_check: If True, perform fresh health checks regardless of cache

        Returns:
            The URL to use for Qdrant connections
        """
        # Sort endpoints by priority
        sorted_endpoints = sorted(self.endpoints, key=lambda e: e.priority)

        for endpoint in sorted_endpoints:
            health = self._health[endpoint.name]

            # Check if we need to re-verify health
            should_check = force_check or self._needs_health_check(endpoint)

            # If currently healthy and no check needed, use it
            if health.status == EndpointStatus.HEALTHY and not should_check:
                self._current_endpoint = endpoint
                self._current_url = endpoint.url
                return endpoint.url

            # If degraded (using backup) and no check needed, use backup
            if health.status == EndpointStatus.DEGRADED and not should_check:
                self._current_endpoint = endpoint
                self._current_url = endpoint.url_backup or endpoint.url
                return self._current_url

            # Perform health check
            if should_check:
                # Try primary URL first
                if self._check_endpoint_health(endpoint, use_backup=False):
                    self._current_endpoint = endpoint
                    self._current_url = endpoint.url
                    return endpoint.url

                # Try backup URL if available
                if endpoint.url_backup and self._check_endpoint_health(endpoint, use_backup=True):
                    self._current_endpoint = endpoint
                    self._current_url = endpoint.url_backup
                    return endpoint.url_backup

        # All endpoints failed - return the primary as fallback
        # (let the actual Qdrant client handle the error)
        if sorted_endpoints:
            primary = sorted_endpoints[0]
            self._current_endpoint = primary
            self._current_url = primary.url
            return primary.url

        # No endpoints configured at all - use localhost default
        return "http://localhost:6333"

    def get_current_status(self) -> Dict[str, any]:
        """Get current routing status for debugging/logging"""
        return {
            "current_endpoint": self._current_endpoint.name if self._current_endpoint else None,
            "current_url": self._current_url,
            "endpoints": {
                ep.name: {
                    "status": self._health[ep.name].status.value,
                    "last_check": self._health[ep.name].last_check.isoformat() if self._health[ep.name].last_check else None,
                    "consecutive_failures": self._health[ep.name].consecutive_failures,
                    "latency_ms": self._health[ep.name].last_latency_ms,
                    "using_backup": self._health[ep.name].using_backup_url,
                    "gpu_enabled": ep.gpu_enabled,
                    "platform": ep.platform,
                }
                for ep in self.endpoints
            }
        }

    def mark_endpoint_failed(self, url: str) -> None:
        """Mark an endpoint as failed after a connection error

        This allows the QdrantSearcher to inform the router when a
        request fails, triggering faster failover.
        """
        for endpoint in self.endpoints:
            if endpoint.url == url or endpoint.url_backup == url:
                health = self._health[endpoint.name]
                health.consecutive_failures += 1
                health.last_check = datetime.now()
                if health.consecutive_failures >= self._failover_after_failures:
                    health.status = EndpointStatus.UNHEALTHY
                break

    def is_primary_available(self) -> bool:
        """Check if the primary (GPU) endpoint is available"""
        for endpoint in self.endpoints:
            if endpoint.is_primary:
                health = self._health[endpoint.name]
                return health.status in (EndpointStatus.HEALTHY, EndpointStatus.DEGRADED)
        return False


# Global router instance (lazy-loaded)
_router: Optional[QdrantRouter] = None


def get_router() -> QdrantRouter:
    """Get global router instance (singleton)"""
    global _router
    if _router is None:
        _router = QdrantRouter()
    return _router


def get_best_qdrant_url(force_check: bool = False) -> str:
    """Convenience function to get best Qdrant URL"""
    return get_router().get_best_url(force_check=force_check)
