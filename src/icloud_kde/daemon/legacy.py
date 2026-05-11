"""Migration for legacy plaintext icloud-linux configuration."""

from __future__ import annotations

import shlex
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from time import strftime

from .secrets import SecretKind, SecretStore, build_secret_ref

MIGRATION_MARKER = "# migrated to KWallet/Secret Service by icloud-kde"
BACKUP_SUFFIX = ".icloud-kde-migrated.bak"
SENSITIVE_KEYS = {"username", "password", "cookie_dir"}


class MigrationAction(str, Enum):
    NONE = "none"
    MIGRATE = "migrate"
    INVALIDATE = "invalidate"


@dataclass(frozen=True, slots=True)
class LegacyPlaintextConfig:
    path: Path
    username: str = ""
    password: str = ""
    cookie_dir: str = ""
    values: dict[str, str] = field(default_factory=dict)

    @property
    def has_plaintext_material(self) -> bool:
        return bool(self.password or self.cookie_dir)


@dataclass(frozen=True, slots=True)
class MigrationPlan:
    action: MigrationAction
    path: Path
    account_label: str = "default"
    backup_path: Path | None = None
    migrated_refs: tuple[str, ...] = ()
    message: str = ""


def load_legacy_plaintext_config(path: str | Path) -> LegacyPlaintextConfig:
    """Load top-level scalar keys from legacy YAML.

    This intentionally recognizes only top-level ``key: value`` scalar pairs.
    Nested YAML is ignored because migration only needs the legacy credential
    keys and default tests must not depend on PyYAML.
    """

    config_path = Path(path).expanduser()
    if not config_path.exists():
        return LegacyPlaintextConfig(path=config_path)
    values = _read_top_level_scalars(config_path)
    return LegacyPlaintextConfig(
        path=config_path,
        username=values.get("username", ""),
        password=values.get("password", ""),
        cookie_dir=values.get("cookie_dir", ""),
        values=values,
    )


def plan_legacy_migration(path: str | Path, store: SecretStore) -> MigrationPlan:
    legacy = load_legacy_plaintext_config(path)
    if not legacy.path.exists() or not legacy.has_plaintext_material:
        return MigrationPlan(
            action=MigrationAction.NONE,
            path=legacy.path,
            message="No legacy plaintext material found.",
        )
    if store.is_available():
        return MigrationPlan(
            action=MigrationAction.MIGRATE,
            path=legacy.path,
            account_label=legacy.username or "default",
            message="Legacy plaintext material will be migrated.",
        )
    return MigrationPlan(
        action=MigrationAction.INVALIDATE,
        path=legacy.path,
        account_label=legacy.username or "default",
        message="Secret store unavailable; legacy plaintext material will be invalidated.",
    )


def apply_legacy_migration(
    path: str | Path,
    store: SecretStore,
    account_label: str = "default",
) -> MigrationPlan:
    legacy = load_legacy_plaintext_config(path)
    planned = plan_legacy_migration(legacy.path, store)
    if planned.action is MigrationAction.NONE:
        return planned

    effective_account = account_label or legacy.username or "default"
    migrated_refs: list[str] = []
    if planned.action is MigrationAction.MIGRATE:
        if legacy.password:
            password_ref = build_secret_ref(effective_account, SecretKind.APPLE_ID_PASSWORD)
            store.store(password_ref, legacy.password.encode("utf-8"))
            migrated_refs.append(password_ref.key())
        if legacy.cookie_dir:
            trust_ref = build_secret_ref(effective_account, SecretKind.TRUST_METADATA)
            store.store(trust_ref, legacy.cookie_dir.encode("utf-8"))
            migrated_refs.append(trust_ref.key())

    backup_path = _backup_path(legacy.path)
    legacy.path.rename(backup_path)
    _chmod_user_rw(backup_path)
    _write_redacted_config(legacy.values, legacy.path)
    _chmod_user_rw(legacy.path)

    return MigrationPlan(
        action=planned.action,
        path=legacy.path,
        account_label=effective_account,
        backup_path=backup_path,
        migrated_refs=tuple(migrated_refs),
        message="Legacy plaintext material migrated."
        if planned.action is MigrationAction.MIGRATE
        else "Legacy plaintext material invalidated.",
    )


def _read_top_level_scalars(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        if not raw_line or raw_line[0].isspace() or raw_line.lstrip().startswith("#"):
            continue
        key, separator, value = raw_line.partition(":")
        if not separator:
            continue
        key = key.strip()
        value = value.split("#", 1)[0].strip()
        if not key:
            continue
        values[key] = _unquote_scalar(value)
    return values


def _unquote_scalar(value: str) -> str:
    if not value:
        return ""
    try:
        return str(shlex.split(value)[0])
    except (ValueError, IndexError):
        return value.strip("\"'")


def _write_redacted_config(values: dict[str, str], path: Path) -> None:
    lines = [MIGRATION_MARKER, "# Legacy credential material was removed."]
    for key in sorted(values):
        if key in SENSITIVE_KEYS:
            continue
        lines.append(f"{key}: {_quote_scalar(values[key])}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _quote_scalar(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _backup_path(path: Path) -> Path:
    timestamp = strftime("%Y%m%d%H%M%S")
    return path.with_name(f"{path.name}.{timestamp}{BACKUP_SUFFIX}")


def _chmod_user_rw(path: Path) -> None:
    try:
        path.chmod(0o600)
    except OSError:
        return
