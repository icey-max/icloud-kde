"""Tests for daemon recovery actions."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from icloud_kde.daemon.config import DaemonConfig  # noqa: E402
from icloud_kde.daemon.recovery import CACHE_REBUILD_TOKEN, RecoveryController  # noqa: E402


class RecoveryControllerTests(unittest.TestCase):
    def _config(self, base: Path) -> DaemonConfig:
        return DaemonConfig(
            sync_root=base / "iCloud",
            cache_dir=base / ".cache" / "icloud-kde",
        )

    def test_reveal_sync_root_reports_path_without_creating_files(self) -> None:
        with TemporaryDirectory() as tmp:
            base = Path(tmp)
            config = self._config(base)
            controller = RecoveryController(config)

            result = controller.reveal_sync_root()

            self.assertTrue(result.ok)
            self.assertEqual(result.path, str(config.sync_root))
            self.assertFalse(config.sync_root.exists())

    def test_collect_logs_copies_existing_sources(self) -> None:
        with TemporaryDirectory() as tmp:
            base = Path(tmp)
            log = base / "daemon.log"
            missing = base / "missing.log"
            destination = base / "logs"
            log.write_text("sync log", encoding="utf-8")
            controller = RecoveryController(self._config(base), log_sources=[log, missing])

            result = controller.collect_logs(destination)

            self.assertTrue(result.ok)
            self.assertEqual((destination / "daemon.log").read_text(encoding="utf-8"), "sync log")

    def test_cache_rebuild_requires_confirmation_token(self) -> None:
        with TemporaryDirectory() as tmp:
            base = Path(tmp)
            config = self._config(base)
            config.cache_dir.mkdir(parents=True)
            controller = RecoveryController(config)

            result = controller.execute_cache_rebuild("wrong-token")

            self.assertFalse(result.ok)
            self.assertTrue(config.cache_dir.exists())

    def test_cache_rebuild_moves_cache_and_preserves_sync_root(self) -> None:
        with TemporaryDirectory() as tmp:
            base = Path(tmp)
            config = self._config(base)
            config.cache_dir.mkdir(parents=True)
            (config.cache_dir / "state.db").write_text("cache", encoding="utf-8")
            config.sync_root.mkdir(parents=True)
            sync_file = config.sync_root / "document.txt"
            sync_file.write_text("local file", encoding="utf-8")
            controller = RecoveryController(config)

            self.assertEqual(controller.prepare_cache_rebuild(), CACHE_REBUILD_TOKEN)
            result = controller.execute_cache_rebuild(CACHE_REBUILD_TOKEN)

            self.assertTrue(result.ok)
            self.assertTrue(config.cache_dir.exists())
            self.assertTrue((Path(result.path) / "state.db").exists())
            self.assertEqual(sync_file.read_text(encoding="utf-8"), "local file")


if __name__ == "__main__":
    unittest.main()
