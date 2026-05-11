"""Non-sensitive daemon configuration and sync-root validation."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

DEFAULT_TUNING: dict[str, Any] = {
    "warmup_mode": "background",
    "upload_interval_seconds": 30,
    "remote_refresh_interval_seconds": 300,
    "warmup_workers": 1,
}


class PathValidationError(ValueError):
    """Raised when a configured local path is unsafe for daemon use."""


@dataclass(frozen=True, slots=True)
class SyncTuning:
    """Background sync tuning with conservative iCloud defaults."""

    warmup_mode: str = "background"
    upload_interval_seconds: int = 30
    remote_refresh_interval_seconds: int = 300
    warmup_workers: int = 1

    def __post_init__(self) -> None:
        if self.warmup_mode not in {"background", "lazy"}:
            raise ValueError("warmup_mode must be 'background' or 'lazy'")
        if self.upload_interval_seconds < 1:
            raise ValueError("upload_interval_seconds must be positive")
        if self.remote_refresh_interval_seconds < 1:
            raise ValueError("remote_refresh_interval_seconds must be positive")
        if self.warmup_workers < 1:
            raise ValueError("warmup_workers must be at least 1")


@dataclass(frozen=True, slots=True)
class DaemonConfig:
    """Project-owned daemon config for local paths and runtime tuning."""

    account_label: str = "default"
    sync_root: Path = field(default_factory=lambda: default_sync_root())
    cache_dir: Path = field(default_factory=lambda: default_cache_dir())
    tuning: SyncTuning = field(default_factory=SyncTuning)
    fuse_allow_other: bool = False
    fuse_read_only: bool = False

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["sync_root"] = str(self.sync_root)
        data["cache_dir"] = str(self.cache_dir)
        return data


def default_cache_dir() -> Path:
    """Return the default internal cache directory for one v1 account."""

    return Path.home() / ".cache" / "icloud-kde" / "default"


def default_sync_root() -> Path:
    """Return the default user-visible sync root."""

    return Path.home() / "iCloud"


def expand_path(path: str | Path) -> Path:
    """Expand a user supplied path without requiring that it already exists."""

    raw = str(path).strip()
    if not raw:
        raise PathValidationError("Path must not be empty")
    return Path(raw).expanduser()


def validate_sync_root(
    sync_root: str | Path,
    cache_dir: str | Path,
    home_dir: str | Path | None = None,
    create: bool = False,
) -> Path:
    """Validate and optionally create the user-visible sync root."""

    requested = expand_path(sync_root)
    cache = expand_path(cache_dir).resolve(strict=False)
    home = expand_path(home_dir or Path.home()).resolve(strict=False)

    if _has_symlink_component(requested):
        raise PathValidationError(f"Sync root must not use symlink components: {requested}")

    resolved = requested.resolve(strict=False)
    if _is_filesystem_root(resolved):
        raise PathValidationError("Sync root must not be the filesystem root")
    if resolved == home:
        raise PathValidationError("Sync root must not be the home directory")
    if _paths_overlap(resolved, cache):
        raise PathValidationError("Sync root must not overlap the cache directory")
    if requested.exists() and not requested.is_dir():
        raise PathValidationError(f"Sync root exists but is not a directory: {requested}")

    if create:
        requested.mkdir(parents=True, exist_ok=True)
    return resolved


def load_config(path: str | Path) -> DaemonConfig:
    """Load daemon config from JSON."""

    config_path = expand_path(path)
    with config_path.open("r", encoding="utf-8") as handle:
        raw = json.load(handle)

    tuning_data = raw.get("tuning", {})
    tuning = SyncTuning(
        warmup_mode=tuning_data.get("warmup_mode", DEFAULT_TUNING["warmup_mode"]),
        upload_interval_seconds=int(
            tuning_data.get(
                "upload_interval_seconds",
                DEFAULT_TUNING["upload_interval_seconds"],
            )
        ),
        remote_refresh_interval_seconds=int(
            tuning_data.get(
                "remote_refresh_interval_seconds",
                DEFAULT_TUNING["remote_refresh_interval_seconds"],
            )
        ),
        warmup_workers=int(tuning_data.get("warmup_workers", DEFAULT_TUNING["warmup_workers"])),
    )
    return DaemonConfig(
        account_label=raw.get("account_label", "default"),
        sync_root=expand_path(raw.get("sync_root", default_sync_root())),
        cache_dir=expand_path(raw.get("cache_dir", default_cache_dir())),
        tuning=tuning,
        fuse_allow_other=bool(raw.get("fuse_allow_other", False)),
        fuse_read_only=bool(raw.get("fuse_read_only", False)),
    )


def save_config(config: DaemonConfig, path: str | Path) -> None:
    """Write daemon config as deterministic JSON."""

    config_path = expand_path(path)
    config_path.parent.mkdir(parents=True, exist_ok=True)
    with config_path.open("w", encoding="utf-8") as handle:
        json.dump(config.to_dict(), handle, indent=2, sort_keys=True)
        handle.write("\n")


def _paths_overlap(left: Path, right: Path) -> bool:
    return _is_relative_to(left, right) or _is_relative_to(right, left)


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def _is_filesystem_root(path: Path) -> bool:
    return path.parent == path


def _has_symlink_component(path: Path) -> bool:
    current = Path(path.anchor) if path.is_absolute() else Path.cwd()
    parts = path.parts[1:] if path.is_absolute() else path.parts
    for part in parts:
        current = current / part
        if current.exists() and current.is_symlink():
            return True
    return False
