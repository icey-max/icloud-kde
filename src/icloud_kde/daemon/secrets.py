"""Secret storage boundary for daemon authentication material."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Protocol, Sequence

DEFAULT_SECRET_SERVICE = "org.kde.ICloudDrive"


class SecretKind(str, Enum):
    APPLE_ID_PASSWORD = "apple_id_password"
    PYICLOUD_SESSION = "pyicloud_session"
    TRUST_METADATA = "trust_metadata"


@dataclass(frozen=True, slots=True)
class SecretRef:
    account_label: str
    kind: SecretKind
    service: str = DEFAULT_SECRET_SERVICE

    def key(self) -> str:
        return f"{self.service}:{self.account_label}:{self.kind.value}"


@dataclass(frozen=True, slots=True)
class SecretRecord:
    ref: SecretRef
    stored: bool = True


class SecretStore(Protocol):
    def store(self, ref: SecretRef, value: bytes) -> SecretRecord:
        """Store bytes for a secret reference."""

    def lookup(self, ref: SecretRef) -> bytes | None:
        """Return stored bytes for a secret reference."""

    def delete(self, ref: SecretRef) -> bool:
        """Delete a secret reference if present."""

    def is_available(self) -> bool:
        """Return whether the backing store can currently be used."""


def build_secret_ref(account_label: str, kind: SecretKind | str) -> SecretRef:
    resolved_kind = kind if isinstance(kind, SecretKind) else SecretKind(kind)
    return SecretRef(account_label=account_label, kind=resolved_kind)


class InMemorySecretStore:
    """Test-only secret store."""

    def __init__(self, available: bool = True) -> None:
        self.available = available
        self._records: dict[str, bytes] = {}

    def store(self, ref: SecretRef, value: bytes) -> SecretRecord:
        self._records[ref.key()] = bytes(value)
        return SecretRecord(ref=ref, stored=True)

    def lookup(self, ref: SecretRef) -> bytes | None:
        value = self._records.get(ref.key())
        return bytes(value) if value is not None else None

    def delete(self, ref: SecretRef) -> bool:
        return self._records.pop(ref.key(), None) is not None

    def is_available(self) -> bool:
        return self.available


Runner = Callable[..., subprocess.CompletedProcess[bytes]]


class SubprocessSecretStore:
    """Secret store backed by the KDE helper command."""

    def __init__(self, command: Sequence[str], runner: Runner | None = None) -> None:
        if not command:
            raise ValueError("command must not be empty")
        self.command = list(command)
        self.runner = runner or subprocess.run

    def store(self, ref: SecretRef, value: bytes) -> SecretRecord:
        result = self.runner(
            self._args("store", ref),
            input=value,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        result.check_returncode()
        return SecretRecord(ref=ref, stored=True)

    def lookup(self, ref: SecretRef) -> bytes | None:
        try:
            result = self.runner(
                self._args("lookup", ref),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
        except OSError:
            return None
        if result.returncode != 0:
            return None
        return result.stdout

    def delete(self, ref: SecretRef) -> bool:
        try:
            result = self.runner(
                self._args("delete", ref),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
        except OSError:
            return False
        return result.returncode == 0

    def is_available(self) -> bool:
        try:
            result = self.runner(
                self.command + ["status"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
        except OSError:
            return False
        return result.returncode == 0

    def _args(self, command: str, ref: SecretRef) -> list[str]:
        return self.command + [
            command,
            "--account",
            ref.account_label,
            "--kind",
            ref.kind.value,
        ]
