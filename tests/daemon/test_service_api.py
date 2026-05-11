"""Tests for transport-independent daemon service API."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from icloud_kde.daemon.config import DaemonConfig, PathValidationError  # noqa: E402
from icloud_kde.daemon.lifecycle import DaemonLifecycle  # noqa: E402
from icloud_kde.daemon.service import DaemonService  # noqa: E402
from icloud_kde.daemon.state import ServiceState  # noqa: E402


class FakeRuntimeFactory:
    def start(self, config: DaemonConfig) -> object:
        return object()

    def stop(self, runtime: object) -> None:
        return None


class FakeRepository:
    def __init__(self) -> None:
        self.entries = {
            "/docs/a.txt": {
                "path": "/docs/a.txt",
                "type": "file",
                "hydrated": True,
                "dirty": False,
                "tombstone": False,
            },
            "/docs/dirty.txt": {
                "path": "/docs/dirty.txt",
                "type": "file",
                "hydrated": True,
                "dirty": True,
                "tombstone": False,
            },
        }

    def get_entry(self, path: str):
        return self.entries.get(path)

    def list_entries(self):
        return list(self.entries.values())

    def list_dirty_entries(self):
        return [entry for entry in self.entries.values() if entry["dirty"]]


class FakeHydrator:
    def __init__(self) -> None:
        self.hydrated: list[str] = []
        self.sync_requested = False

    def hydrate(self, path: str) -> None:
        self.hydrated.append(path)

    def request_sync(self) -> None:
        self.sync_requested = True

    def get_progress(self):
        return {"total": 2, "completed": 1}


class DaemonServiceApiTests(unittest.TestCase):
    def _service(self, base: Path) -> DaemonService:
        lifecycle = DaemonLifecycle(FakeRuntimeFactory())
        lifecycle.configure(
            DaemonConfig(
                sync_root=base / "iCloud",
                cache_dir=base / ".cache" / "icloud-kde",
            )
        )
        return DaemonService(lifecycle, FakeRepository(), FakeHydrator())

    def test_status_returns_project_owned_dict(self) -> None:
        with TemporaryDirectory() as tmp:
            service = self._service(Path(tmp))

            status = service.get_status()

            self.assertEqual(status["state"], "idle")
            self.assertEqual(status["progress"], {"total": 2, "completed": 1})
            self.assertIsInstance(status, dict)
            self.assertNotIn("_runtime", status)

    def test_missing_item_state_includes_requested_path(self) -> None:
        with TemporaryDirectory() as tmp:
            service = self._service(Path(tmp))

            state = service.get_item_state("/missing.txt")

            self.assertEqual(state["path"], "/missing.txt")
            self.assertEqual(state["state"], "error")
            self.assertEqual(state["message"], "item not found")

    def test_pause_resume_are_safe_controls(self) -> None:
        with TemporaryDirectory() as tmp:
            service = self._service(Path(tmp))

            paused = service.pause()
            resumed = service.resume()

            self.assertEqual(paused["state"], "paused")
            self.assertTrue(paused["paused"])
            self.assertEqual(resumed["state"], "idle")
            self.assertFalse(resumed["paused"])

    def test_resume_preserves_underlying_blocker_state(self) -> None:
        with TemporaryDirectory() as tmp:
            service = self._service(Path(tmp))
            service.service_state = ServiceState.AUTH_REQUIRED

            paused = service.pause()
            resumed = service.resume()

            self.assertEqual(paused["state"], "paused")
            self.assertEqual(resumed["state"], "auth_required")

    def test_set_sync_root_validates_path(self) -> None:
        with TemporaryDirectory() as tmp:
            base = Path(tmp)
            service = self._service(base)
            target = base / "New iCloud"
            bad_file = base / "bad"
            bad_file.write_text("x", encoding="utf-8")

            updated = service.set_sync_root(str(target))
            with self.assertRaises(PathValidationError):
                service.set_sync_root(str(bad_file))

            self.assertEqual(updated["sync_root"], str(target.resolve()))
            self.assertTrue(target.is_dir())

    def test_no_destructive_controls_are_exposed(self) -> None:
        names = set(dir(DaemonService))

        self.assertFalse(
            {
                "delete",
                "purge",
                "reset",
                "force_overwrite",
                "resolve_conflict",
                "clear_cache",
            }
            & names
        )

    def test_list_problem_items_reports_unsupported_filesystem_entries(self) -> None:
        with TemporaryDirectory() as tmp:
            base = Path(tmp)
            service = self._service(base)
            target = base / "target.txt"
            target.write_text("target", encoding="utf-8")
            (base / "iCloud" / "link").symlink_to(target)

            problems = service.list_problem_items()

            unsupported = [
                problem for problem in problems if problem["kind"] == "unsupported_file_type"
            ]
            self.assertEqual(len(unsupported), 1)
            self.assertEqual(unsupported[0]["path"], "/link")
            self.assertEqual(unsupported[0]["severity"], "warning")
            self.assertEqual(unsupported[0]["state"], "unsupported")
            self.assertTrue(unsupported[0]["message"])


if __name__ == "__main__":
    unittest.main()
