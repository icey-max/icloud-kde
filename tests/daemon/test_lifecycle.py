"""Tests for daemon lifecycle ownership."""

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
from icloud_kde.daemon.lifecycle import DaemonLifecycle  # noqa: E402


class FakeRuntimeFactory:
    def __init__(self) -> None:
        self.started: list[DaemonConfig] = []
        self.stopped: list[object] = []
        self.runtime = object()

    def start(self, config: DaemonConfig) -> object:
        self.started.append(config)
        return self.runtime

    def stop(self, runtime: object) -> None:
        self.stopped.append(runtime)


class DaemonLifecycleTests(unittest.TestCase):
    def _config(self, base: Path) -> DaemonConfig:
        return DaemonConfig(
            sync_root=base / "iCloud",
            cache_dir=base / ".cache" / "icloud-kde",
        )

    def test_lifecycle_starts_and_stops_runtime_once(self) -> None:
        with TemporaryDirectory() as tmp:
            base = Path(tmp)
            factory = FakeRuntimeFactory()
            lifecycle = DaemonLifecycle(factory)
            lifecycle.configure(self._config(base))

            first = lifecycle.start()
            second = lifecycle.start()
            stopped = lifecycle.stop()
            lifecycle.stop()

            self.assertTrue(first.running)
            self.assertTrue(second.running)
            self.assertFalse(stopped.running)
            self.assertEqual(len(factory.started), 1)
            self.assertEqual(factory.stopped, [factory.runtime])
            self.assertTrue((base / "iCloud").is_dir())

    def test_lifecycle_pause_resume_preserves_runtime(self) -> None:
        with TemporaryDirectory() as tmp:
            base = Path(tmp)
            factory = FakeRuntimeFactory()
            lifecycle = DaemonLifecycle(factory)
            lifecycle.configure(self._config(base))
            lifecycle.start()

            paused = lifecycle.pause()
            resumed = lifecycle.resume()

            self.assertTrue(paused.running)
            self.assertTrue(paused.paused)
            self.assertTrue(resumed.running)
            self.assertFalse(resumed.paused)
            self.assertEqual(len(factory.started), 1)
            self.assertEqual(factory.stopped, [])

    def test_lifecycle_requires_configuration_before_start(self) -> None:
        lifecycle = DaemonLifecycle(FakeRuntimeFactory())

        with self.assertRaises(RuntimeError):
            lifecycle.start()

    def test_status_reports_sync_root_cache_and_paused_state(self) -> None:
        with TemporaryDirectory() as tmp:
            base = Path(tmp)
            lifecycle = DaemonLifecycle(FakeRuntimeFactory())
            config = self._config(base)
            lifecycle.configure(config)
            lifecycle.pause()

            status = lifecycle.status()
            payload = status.to_dict()

            self.assertFalse(status.running)
            self.assertTrue(status.paused)
            self.assertEqual(status.sync_root, config.sync_root)
            self.assertEqual(status.cache_dir, config.cache_dir)
            self.assertEqual(payload["sync_root"], str(config.sync_root))
            self.assertEqual(payload["cache_dir"], str(config.cache_dir))
            self.assertEqual(payload["message"], "paused")


if __name__ == "__main__":
    unittest.main()
