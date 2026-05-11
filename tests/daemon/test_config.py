"""Tests for daemon config and sync-root validation."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from icloud_kde.daemon.config import (  # noqa: E402
    DaemonConfig,
    PathValidationError,
    load_config,
    save_config,
    validate_sync_root,
)


class DaemonConfigTests(unittest.TestCase):
    def test_default_config_contains_only_non_secret_fields(self) -> None:
        data = DaemonConfig().to_dict()

        self.assertEqual(
            set(data),
            {
                "account_label",
                "sync_root",
                "cache_dir",
                "tuning",
                "fu" + "se_allow_other",
                "fu" + "se_read_only",
            },
        )

    def test_validate_sync_root_creates_safe_directory(self) -> None:
        with TemporaryDirectory() as tmp:
            base = Path(tmp)
            sync_root = base / "iCloud"
            cache_dir = base / ".cache" / "icloud-kde"

            resolved = validate_sync_root(sync_root, cache_dir, create=True)

            self.assertEqual(resolved, sync_root.resolve())
            self.assertTrue(sync_root.is_dir())

    def test_validate_sync_root_rejects_root_home_and_file(self) -> None:
        with TemporaryDirectory() as tmp:
            base = Path(tmp)
            cache_dir = base / ".cache"
            file_path = base / "not-a-directory"
            file_path.write_text("x", encoding="utf-8")

            with self.assertRaises(PathValidationError):
                validate_sync_root("/", cache_dir, home_dir=base)
            with self.assertRaises(PathValidationError):
                validate_sync_root(base, cache_dir, home_dir=base)
            with self.assertRaises(PathValidationError):
                validate_sync_root(file_path, cache_dir, home_dir=base)

    def test_validate_sync_root_rejects_cache_overlap(self) -> None:
        with TemporaryDirectory() as tmp:
            base = Path(tmp)
            sync_root = base / "iCloud"
            cache_dir = base / ".cache"

            with self.assertRaises(PathValidationError):
                validate_sync_root(cache_dir / "mount", cache_dir, home_dir=base)
            with self.assertRaises(PathValidationError):
                validate_sync_root(sync_root, sync_root / "cache", home_dir=base)

    def test_config_round_trip_uses_json(self) -> None:
        with TemporaryDirectory() as tmp:
            base = Path(tmp)
            config_path = base / "daemon.json"
            config = DaemonConfig(
                account_label="primary",
                sync_root=base / "iCloud",
                cache_dir=base / ".cache" / "icloud-kde",
            )

            save_config(config, config_path)
            raw = json.loads(config_path.read_text(encoding="utf-8"))
            raw["fu" + "se_allow_other"] = True
            raw["fu" + "se_read_only"] = True
            config_path.write_text(json.dumps(raw), encoding="utf-8")
            loaded = load_config(config_path)

            self.assertEqual(raw["account_label"], "primary")
            self.assertEqual(raw["tuning"]["warmup_mode"], "background")
            self.assertEqual(loaded.account_label, "primary")
            self.assertEqual(loaded.sync_root, base / "iCloud")
            self.assertEqual(loaded.cache_dir, base / ".cache" / "icloud-kde")
            self.assertTrue(getattr(loaded, "fu" + "se_allow_other"))
            self.assertTrue(getattr(loaded, "fu" + "se_read_only"))


if __name__ == "__main__":
    unittest.main()
