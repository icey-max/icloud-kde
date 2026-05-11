"""Tests for legacy plaintext configuration migration."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from icloud_kde.daemon.legacy import (  # noqa: E402
    MigrationAction,
    apply_legacy_migration,
    load_legacy_plaintext_config,
)
from icloud_kde.daemon.secrets import (  # noqa: E402
    InMemorySecretStore,
    SecretKind,
    build_secret_ref,
)


def write_legacy_config(path: Path) -> None:
    path.write_text(
        "\n".join(
            [
                "---",
                'username: "jane@example.com"',
                "password: 'apple-password'",
                'cache_dir: "~/.cache/icloud-linux"',
                'cookie_dir: "~/.config/icloud-linux/cookies"',
                'warmup_mode: "background"',
                "fuse_options:",
                "  allow_other: false",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


class LegacyMigrationTests(unittest.TestCase):
    def test_load_legacy_plaintext_config_detects_username_password_cookie_dir(self) -> None:
        with TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "config.yaml"
            write_legacy_config(config_path)

            loaded = load_legacy_plaintext_config(config_path)

            self.assertEqual(loaded.username, "jane@example.com")
            self.assertEqual(loaded.password, "apple-password")
            self.assertEqual(loaded.cookie_dir, "~/.config/icloud-linux/cookies")

    def test_apply_migration_moves_password_to_secret_store(self) -> None:
        with TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "config.yaml"
            write_legacy_config(config_path)
            store = InMemorySecretStore()

            result = apply_legacy_migration(config_path, store, account_label="primary")

            self.assertEqual(result.action, MigrationAction.MIGRATE)
            password_ref = build_secret_ref("primary", SecretKind.APPLE_ID_PASSWORD)
            trust_ref = build_secret_ref("primary", SecretKind.TRUST_METADATA)
            self.assertEqual(store.lookup(password_ref), b"apple-password")
            self.assertEqual(store.lookup(trust_ref), b"~/.config/icloud-linux/cookies")

    def test_apply_invalidation_removes_plaintext_when_store_unavailable(self) -> None:
        with TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "config.yaml"
            write_legacy_config(config_path)
            store = InMemorySecretStore(available=False)

            result = apply_legacy_migration(config_path, store)

            self.assertEqual(result.action, MigrationAction.INVALIDATE)
            replacement = config_path.read_text(encoding="utf-8")
            self.assertNotIn("jane@example.com", replacement)
            self.assertNotIn("apple-password", replacement)
            self.assertNotIn("cookie_dir", replacement)

    def test_apply_migration_preserves_backup_and_redacts_replacement(self) -> None:
        with TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "config.yaml"
            write_legacy_config(config_path)
            store = InMemorySecretStore()

            result = apply_legacy_migration(config_path, store)

            backups = list(Path(tmp).glob("*.icloud-kde-migrated.bak"))
            self.assertEqual(backups, [result.backup_path])
            self.assertIn("apple-password", backups[0].read_text(encoding="utf-8"))

            replacement = config_path.read_text(encoding="utf-8")
            self.assertIn("# migrated to KWallet/Secret Service by icloud-kde", replacement)
            self.assertIn("cache_dir", replacement)
            self.assertNotIn("username", replacement)
            self.assertNotIn("password", replacement)
            self.assertNotIn("cookie_dir", replacement)


if __name__ == "__main__":
    unittest.main()
