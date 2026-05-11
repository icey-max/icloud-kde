"""Public daemon state DTOs and sync-state mapping."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping


class ItemState(str, Enum):
    HYDRATED = "hydrated"
    PLACEHOLDER = "placeholder"
    DIRTY = "dirty"
    SYNCING = "syncing"
    CONFLICTED = "conflicted"
    OFFLINE = "offline"
    AUTH_REQUIRED = "auth_required"
    UNSUPPORTED = "unsupported"
    ERROR = "error"


class ServiceState(str, Enum):
    STARTING = "starting"
    SCANNING = "scanning"
    IDLE = "idle"
    SYNCING = "syncing"
    PAUSED = "paused"
    OFFLINE = "offline"
    AUTH_REQUIRED = "auth_required"
    ACCOUNT_BLOCKED = "account_blocked"
    WEB_ACCESS_BLOCKED = "web_access_blocked"
    DEGRADED = "degraded"
    STOPPING = "stopping"


class ProblemKind(str, Enum):
    CONFLICT = "conflict"
    DIRTY = "dirty"
    AUTH_REQUIRED = "auth_required"
    ACCOUNT_BLOCKED = "account_blocked"
    WEB_ACCESS_BLOCKED = "web_access_blocked"
    OFFLINE = "offline"
    UNSUPPORTED_FILE_TYPE = "unsupported_file_type"
    ERROR = "error"


class ProblemSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass(frozen=True, slots=True)
class ItemStatus:
    path: str
    state: ItemState
    item_type: str = "file"
    size: int = 0
    mtime: int = 0
    message: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "path": self.path,
            "state": self.state.value,
            "item_type": self.item_type,
            "size": self.size,
            "mtime": self.mtime,
            "message": self.message,
        }


@dataclass(frozen=True, slots=True)
class ServiceStatus:
    state: ServiceState
    sync_root: str = ""
    cache_dir: str = ""
    paused: bool = False
    message: str = ""
    progress: Mapping[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return {
            "state": self.state.value,
            "sync_root": self.sync_root,
            "cache_dir": self.cache_dir,
            "paused": self.paused,
            "message": self.message,
            "progress": dict(self.progress),
        }


@dataclass(frozen=True, slots=True)
class ProgressStatus:
    syncing: bool = False
    total: int = 0
    completed: int = 0
    message: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "syncing": self.syncing,
            "total": self.total,
            "completed": self.completed,
            "message": self.message,
        }


@dataclass(frozen=True, slots=True)
class ProblemItem:
    path: str
    kind: ProblemKind
    severity: ProblemSeverity
    state: ItemState
    message: str

    def to_dict(self) -> dict[str, object]:
        return {
            "path": self.path,
            "kind": self.kind.value,
            "severity": self.severity.value,
            "state": self.state.value,
            "message": self.message,
        }


def item_status_from_entry(
    entry: Mapping[str, Any] | None,
    service_state: ServiceState = ServiceState.IDLE,
    syncing_paths: set[str] | None = None,
    conflict_paths: set[str] | None = None,
    unsupported_paths: set[str] | None = None,
    requested_path: str = "",
) -> ItemStatus:
    if entry is None:
        return ItemStatus(path=requested_path, state=ItemState.ERROR, message="item not found")
    return ItemStatus(
        path=str(entry.get("path", "")),
        state=item_state_from_entry(
            entry,
            service_state=service_state,
            syncing_paths=syncing_paths,
            conflict_paths=conflict_paths,
            unsupported_paths=unsupported_paths,
        ),
        item_type=str(entry.get("type", "file")),
        size=int(entry.get("size", 0) or 0),
        mtime=int(entry.get("mtime", 0) or 0),
    )


def item_state_from_entry(
    entry: Mapping[str, Any],
    service_state: ServiceState = ServiceState.IDLE,
    syncing_paths: set[str] | None = None,
    conflict_paths: set[str] | None = None,
    unsupported_paths: set[str] | None = None,
) -> ItemState:
    path = str(entry.get("path", ""))
    syncing = syncing_paths or set()
    conflicts = conflict_paths or set()
    unsupported = unsupported_paths or set()

    if path in unsupported:
        return ItemState.UNSUPPORTED
    if path in conflicts:
        return ItemState.CONFLICTED
    if bool(entry.get("dirty")) or bool(entry.get("tombstone")):
        return ItemState.DIRTY
    if path in syncing:
        return ItemState.SYNCING
    if service_state in {
        ServiceState.AUTH_REQUIRED,
        ServiceState.ACCOUNT_BLOCKED,
        ServiceState.WEB_ACCESS_BLOCKED,
    }:
        return ItemState.AUTH_REQUIRED
    if service_state is ServiceState.OFFLINE:
        return ItemState.OFFLINE
    if str(entry.get("type", "file")) == "file" and not bool(entry.get("hydrated")):
        return ItemState.PLACEHOLDER
    if bool(entry.get("hydrated")):
        return ItemState.HYDRATED
    return ItemState.HYDRATED
