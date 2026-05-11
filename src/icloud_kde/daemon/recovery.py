"""Recovery actions exposed through the daemon service."""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from time import strftime
from typing import Sequence

from .config import DaemonConfig

CACHE_REBUILD_TOKEN = "rebuild-cache"


class RecoveryAction(str, Enum):
    REQUEST_REAUTH = "request_reauth"
    COLLECT_LOGS = "collect_logs"
    REVEAL_SYNC_ROOT = "reveal_sync_root"
    REBUILD_CACHE = "rebuild_cache"


@dataclass(frozen=True, slots=True)
class RecoveryResult:
    action: RecoveryAction
    ok: bool
    message: str
    path: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "action": self.action.value,
            "ok": self.ok,
            "message": self.message,
            "path": self.path,
        }


class RecoveryController:
    def __init__(
        self,
        config: DaemonConfig,
        log_sources: Sequence[Path] | None = None,
    ) -> None:
        self.config = config
        self.log_sources = list(log_sources or [])

    def request_reauth(self) -> RecoveryResult:
        return RecoveryResult(
            action=RecoveryAction.REQUEST_REAUTH,
            ok=True,
            message="Re-authentication requested.",
        )

    def reveal_sync_root(self) -> RecoveryResult:
        return RecoveryResult(
            action=RecoveryAction.REVEAL_SYNC_ROOT,
            ok=True,
            message="Sync root ready to reveal.",
            path=str(self.config.sync_root),
        )

    def collect_logs(self, destination: str | Path) -> RecoveryResult:
        target = Path(destination).expanduser()
        target.mkdir(parents=True, exist_ok=True)
        copied = 0
        for source in self.log_sources:
            if source.is_file():
                shutil.copy2(source, target / source.name)
                copied += 1
        return RecoveryResult(
            action=RecoveryAction.COLLECT_LOGS,
            ok=True,
            message=f"Collected {copied} log file(s).",
            path=str(target),
        )

    def prepare_cache_rebuild(self) -> str:
        return CACHE_REBUILD_TOKEN

    def execute_cache_rebuild(self, confirm_token: str) -> RecoveryResult:
        if confirm_token != CACHE_REBUILD_TOKEN:
            return RecoveryResult(
                action=RecoveryAction.REBUILD_CACHE,
                ok=False,
                message="Cache rebuild confirmation token did not match.",
            )

        cache_dir = self.config.cache_dir
        backup_root = cache_dir.parent / "cache-rebuild-backups"
        backup_root.mkdir(parents=True, exist_ok=True)
        backup_path = backup_root / strftime("%Y%m%d%H%M%S")
        if cache_dir.exists():
            shutil.move(str(cache_dir), str(backup_path))
        cache_dir.mkdir(parents=True, exist_ok=True)
        return RecoveryResult(
            action=RecoveryAction.REBUILD_CACHE,
            ok=True,
            message="Cache moved to backup and recreated.",
            path=str(backup_path),
        )
