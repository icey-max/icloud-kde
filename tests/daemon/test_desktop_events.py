"""Tests for daemon-owned desktop event state used by KDE clients."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from icloud_kde.daemon.auth import AuthState, FakeAuthController  # noqa: E402
from icloud_kde.daemon.config import DaemonConfig  # noqa: E402
from icloud_kde.daemon.lifecycle import DaemonLifecycle  # noqa: E402
from icloud_kde.daemon.service import DaemonService  # noqa: E402
from icloud_kde.daemon.state import ProblemKind, ServiceState  # noqa: E402


class FakeRuntimeFactory:
    def start(self, config: DaemonConfig) -> object:
        return object()

    def stop(self, runtime: object) -> None:
        return None


class FakeRepository:
    def __init__(self) -> None:
        self.entries = {
            "/docs/clean.txt": {
                "path": "/docs/clean.txt",
                "type": "file",
                "hydrated": True,
                "dirty": False,
                "tombstone": False,
            },
            "/docs/conflict.txt": {
                "path": "/docs/conflict.txt",
                "type": "file",
                "hydrated": True,
                "dirty": False,
                "tombstone": False,
            },
            "/docs/stuck.txt": {
                "path": "/docs/stuck.txt",
                "type": "file",
                "hydrated": True,
                "dirty": True,
                "tombstone": False,
                "upload_stuck": True,
            },
            "/docs/hydrated.txt": {
                "path": "/docs/hydrated.txt",
                "type": "file",
                "hydrated": True,
                "dirty": False,
                "tombstone": False,
            },
        }

    def get_entry(self, path: str):
        return self.entries.get(path)

    def list_entries(self):
        return list(self.entries.values())

    def list_dirty_entries(self):
        return [
            entry
            for entry in self.entries.values()
            if entry.get("dirty") or entry.get("tombstone")
        ]


class FakeHydrator:
    def __init__(self) -> None:
        self.hydrated: list[str] = []
        self.sync_requested = False

    def hydrate(self, path: str) -> None:
        self.hydrated.append(path)

    def request_sync(self) -> None:
        self.sync_requested = True

    def get_progress(self):
        return {"total": 1, "completed": 1, "foreground": True}


class DesktopEventTests(unittest.TestCase):
    def _service(
        self,
        base: Path,
        *,
        service_state: ServiceState = ServiceState.IDLE,
        auth_state: AuthState = AuthState.TRUSTED,
    ) -> DaemonService:
        lifecycle = DaemonLifecycle(FakeRuntimeFactory())
        lifecycle.configure(
            DaemonConfig(
                sync_root=base / "iCloud",
                cache_dir=base / ".cache" / "icloud-kde",
            )
        )
        return DaemonService(
            lifecycle,
            FakeRepository(),
            FakeHydrator(),
            service_state=service_state,
            conflict_paths={"/docs/conflict.txt"},
            stuck_upload_paths={"/docs/stuck.txt"},
            foreground_hydration_paths={"/docs/hydrated.txt"},
            auth_controller=FakeAuthController(initial_state=auth_state),
        )

    def test_problem_kind_includes_upload_stuck_string_value(self) -> None:
        self.assertEqual(ProblemKind.UPLOAD_STUCK.value, "upload_stuck")

    def test_auth_required_status_is_visible_for_desktop_clients(self) -> None:
        with TemporaryDirectory() as tmp:
            service = self._service(
                Path(tmp),
                service_state=ServiceState.AUTH_REQUIRED,
                auth_state=AuthState.AUTH_REQUIRED,
            )

            status = service.get_status()
            auth = service.get_auth_status()

            self.assertEqual(status["state"], "auth_required")
            self.assertEqual(auth["state"], "auth_required")
            self.assertNotIn("password", str(auth).lower())

    def test_account_and_web_blockers_are_problem_items(self) -> None:
        with TemporaryDirectory() as tmp:
            for state, kind in [
                (ServiceState.ACCOUNT_BLOCKED, "account_blocked"),
                (ServiceState.WEB_ACCESS_BLOCKED, "web_access_blocked"),
                (ServiceState.AUTH_REQUIRED, "auth_required"),
            ]:
                service = self._service(Path(tmp), service_state=state)

                problems = service.list_problem_items()

                blocker = [problem for problem in problems if problem["kind"] == kind]
                self.assertEqual(len(blocker), 1)
                self.assertEqual(blocker[0]["severity"], "error")
                self.assertEqual(blocker[0]["state"], "auth_required")

    def test_conflict_problem_is_warning_with_review_copy(self) -> None:
        with TemporaryDirectory() as tmp:
            service = self._service(Path(tmp))

            problems = service.list_problem_items()
            conflict = [problem for problem in problems if problem["kind"] == "conflict"][0]

            self.assertEqual(conflict["severity"], "warning")
            self.assertEqual(conflict["state"], "conflicted")
            self.assertIn("review", conflict["message"].lower())

    def test_upload_stuck_problem_uses_daemon_owned_state(self) -> None:
        with TemporaryDirectory() as tmp:
            service = self._service(Path(tmp))

            problems = service.list_problem_items()
            stuck = [problem for problem in problems if problem["kind"] == "upload_stuck"]

            self.assertEqual(len(stuck), 1)
            self.assertEqual(stuck[0]["severity"], "warning")
            self.assertEqual(stuck[0]["state"], "dirty")
            self.assertIn("repeated attempts", stuck[0]["message"])
            self.assertNotIn(str(Path(tmp).home()), stuck[0]["message"])
            self.assertNotIn("@", stuck[0]["message"])

    def test_pause_resume_state_transitions_are_desktop_visible(self) -> None:
        with TemporaryDirectory() as tmp:
            service = self._service(Path(tmp))

            paused = service.pause()
            resumed = service.resume()

            self.assertEqual(paused["state"], "paused")
            self.assertTrue(paused["paused"])
            self.assertEqual(resumed["state"], "idle")
            self.assertFalse(resumed["paused"])

    def test_foreground_hydration_completion_state_is_explicit(self) -> None:
        with TemporaryDirectory() as tmp:
            service = self._service(Path(tmp))

            item = service.get_item_state("/docs/hydrated.txt")

            self.assertEqual(item["state"], "hydrated")
            self.assertTrue(item["foreground_hydration"])
            self.assertIn("available locally", item["message"].lower())


if __name__ == "__main__":
    unittest.main()
