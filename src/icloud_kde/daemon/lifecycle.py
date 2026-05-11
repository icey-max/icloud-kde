"""Daemon runtime ownership and lifecycle state."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from .config import DaemonConfig, validate_sync_root


class RuntimeFactory(Protocol):
    """Factory used by the daemon lifecycle to start and stop sync runtime."""

    def start(self, config: DaemonConfig) -> object:
        """Start runtime for the provided config."""

    def stop(self, runtime: object) -> None:
        """Stop a previously started runtime."""


class UnconfiguredRuntimeFactory:
    """Placeholder factory for callers that have not wired the real runtime yet."""

    def start(self, config: DaemonConfig) -> object:
        raise RuntimeError("No runtime factory configured")

    def stop(self, runtime: object) -> None:
        return None


@dataclass(frozen=True, slots=True)
class LifecycleStatus:
    """Snapshot of daemon lifecycle state."""

    running: bool
    paused: bool
    sync_root: Path | None
    cache_dir: Path | None
    message: str

    def to_dict(self) -> dict[str, object]:
        return {
            "running": self.running,
            "paused": self.paused,
            "sync_root": str(self.sync_root) if self.sync_root else "",
            "cache_dir": str(self.cache_dir) if self.cache_dir else "",
            "message": self.message,
        }


class DaemonLifecycle:
    """Single owner for daemon runtime start, stop, pause, and resume."""

    def __init__(self, runtime_factory: RuntimeFactory | None = None) -> None:
        self._runtime_factory: RuntimeFactory = runtime_factory or UnconfiguredRuntimeFactory()
        self._config: DaemonConfig | None = None
        self._runtime: object | None = None
        self._paused = False

    def configure(self, config: DaemonConfig) -> None:
        validate_sync_root(config.sync_root, config.cache_dir, create=True)
        self._config = config

    def start(self) -> LifecycleStatus:
        if self._config is None:
            raise RuntimeError("DaemonLifecycle must be configured before start")
        if self._runtime is None:
            self._runtime = self._runtime_factory.start(self._config)
        return self.status()

    def stop(self) -> LifecycleStatus:
        if self._runtime is not None:
            runtime = self._runtime
            self._runtime = None
            self._runtime_factory.stop(runtime)
        self._paused = False
        return self.status()

    def pause(self) -> LifecycleStatus:
        self._paused = True
        return self.status("paused")

    def resume(self) -> LifecycleStatus:
        self._paused = False
        return self.status("running" if self.is_running() else "stopped")

    def status(self, message: str | None = None) -> LifecycleStatus:
        return LifecycleStatus(
            running=self.is_running(),
            paused=self._paused,
            sync_root=self._config.sync_root if self._config else None,
            cache_dir=self._config.cache_dir if self._config else None,
            message=message or self._status_message(),
        )

    def is_running(self) -> bool:
        return self._runtime is not None

    @property
    def config(self) -> DaemonConfig | None:
        return self._config

    def _status_message(self) -> str:
        if self._config is None:
            return "not configured"
        if self._paused:
            return "paused"
        if self.is_running():
            return "running"
        return "stopped"
