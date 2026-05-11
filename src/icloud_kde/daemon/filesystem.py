"""Filesystem semantics classification for the daemon sync root."""

from __future__ import annotations

import os
import stat
from dataclasses import dataclass
from pathlib import Path

SUPPORTED_FILE_TYPES = {"regular_file", "directory"}
UNSUPPORTED_FILE_TYPES = {"symlink", "socket", "device", "fifo", "unknown"}


@dataclass(frozen=True, slots=True)
class FileSemantics:
    path: Path
    file_type: str
    supported: bool
    reason: str = ""


@dataclass(frozen=True, slots=True)
class UnsupportedEntry:
    path: str
    file_type: str
    reason: str

    def to_dict(self) -> dict[str, str]:
        return {
            "path": self.path,
            "file_type": self.file_type,
            "reason": self.reason,
        }


def classify_path(path: str | Path) -> FileSemantics:
    target = Path(path)
    try:
        mode = os.lstat(target).st_mode
    except OSError as exc:
        return FileSemantics(
            path=target,
            file_type="unknown",
            supported=False,
            reason=f"Unable to inspect filesystem entry: {exc.strerror or exc}",
        )

    if stat.S_ISREG(mode):
        return FileSemantics(target, "regular_file", True)
    if stat.S_ISDIR(mode):
        return FileSemantics(target, "directory", True)
    if stat.S_ISLNK(mode):
        return FileSemantics(target, "symlink", False, "Symlinks are unsupported in v1.")
    if stat.S_ISSOCK(mode):
        return FileSemantics(target, "socket", False, "Sockets are unsupported in v1.")
    if stat.S_ISFIFO(mode):
        return FileSemantics(target, "fifo", False, "FIFOs are unsupported in v1.")
    if stat.S_ISCHR(mode) or stat.S_ISBLK(mode):
        return FileSemantics(target, "device", False, "Device files are unsupported in v1.")
    return FileSemantics(target, "unknown", False, "Unknown filesystem entries are unsupported in v1.")


def is_supported_path(path: str | Path) -> bool:
    return classify_path(path).supported


def unsupported_reason(path: str | Path) -> str:
    semantics = classify_path(path)
    return "" if semantics.supported else semantics.reason


def scan_unsupported_entries(root: str | Path) -> list[UnsupportedEntry]:
    root_path = Path(root)
    root_semantics = classify_path(root_path)
    if not root_semantics.supported:
        return [
            UnsupportedEntry(
                path="/",
                file_type=root_semantics.file_type,
                reason=root_semantics.reason,
            )
        ]
    if root_semantics.file_type != "directory":
        return []

    unsupported: list[UnsupportedEntry] = []
    for current, dirnames, filenames in os.walk(root_path, topdown=True, followlinks=False):
        current_path = Path(current)

        for dirname in list(dirnames):
            candidate = current_path / dirname
            semantics = classify_path(candidate)
            if semantics.supported:
                continue
            unsupported.append(_entry_for(root_path, candidate, semantics))
            dirnames.remove(dirname)

        for filename in filenames:
            candidate = current_path / filename
            semantics = classify_path(candidate)
            if not semantics.supported:
                unsupported.append(_entry_for(root_path, candidate, semantics))

    return sorted(unsupported, key=lambda entry: entry.path)


def _entry_for(root: Path, path: Path, semantics: FileSemantics) -> UnsupportedEntry:
    return UnsupportedEntry(
        path=_relative_posix_path(root, path),
        file_type=semantics.file_type,
        reason=semantics.reason,
    )


def _relative_posix_path(root: Path, path: Path) -> str:
    return "/" + path.relative_to(root).as_posix()
