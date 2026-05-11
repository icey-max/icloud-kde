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

from icloud_kde.daemon.auth import FakeAuthController  # noqa: E402
from icloud_kde.daemon.config import DaemonConfig, PathValidationError  # noqa: E402
from icloud_kde.daemon.lifecycle import DaemonLifecycle  # noqa: E402
from icloud_kde.daemon.recovery import CACHE_REBUILD_TOKEN, RecoveryController  # noqa: E402
from icloud_kde.daemon.service import DaemonService  # noqa: E402
from icloud_kde.daemon.secrets import SecretKind, build_secret_ref  # noqa: E402
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

    def test_auth_methods_use_password_secret_ref(self) -> None:
        with TemporaryDirectory() as tmp:
            service = self._service(Path(tmp))
            service.auth_controller = FakeAuthController(requires_2fa=True)
            ref = build_secret_ref("default", SecretKind.APPLE_ID_PASSWORD)

            challenge = service.begin_sign_in("jane@example.com", ref.key())
            trusted = service.submit_two_factor_code("123456")

            self.assertEqual(challenge["state"], "needs_2fa")
            self.assertEqual(trusted["state"], "trusted")
            self.assertNotIn("password", str(challenge).lower())

    def test_auth_methods_reject_raw_password_ref(self) -> None:
        with TemporaryDirectory() as tmp:
            service = self._service(Path(tmp))

            with self.assertRaises(ValueError):
                service.begin_sign_in("jane@example.com", "raw-password")

    def test_recovery_methods_cover_reauth_logs_rebuild_and_reveal(self) -> None:
        with TemporaryDirectory() as tmp:
            base = Path(tmp)
            config = DaemonConfig(
                sync_root=base / "iCloud",
                cache_dir=base / ".cache" / "icloud-kde",
            )
            config.sync_root.mkdir(parents=True)
            (config.sync_root / "document.txt").write_text("local", encoding="utf-8")
            config.cache_dir.mkdir(parents=True)
            (config.cache_dir / "state.db").write_text("cache", encoding="utf-8")
            log = base / "daemon.log"
            log.write_text("log", encoding="utf-8")
            lifecycle = DaemonLifecycle(FakeRuntimeFactory())
            lifecycle.configure(config)
            service = DaemonService(
                lifecycle,
                FakeRepository(),
                FakeHydrator(),
                recovery_controller=RecoveryController(config, [log]),
            )

            reauth = service.request_reauth()
            logs = service.collect_logs(str(base / "logs"))
            reveal = service.reveal_sync_root()
            rebuilt = service.rebuild_cache(CACHE_REBUILD_TOKEN)

            self.assertEqual(reauth["action"], "request_reauth")
            self.assertTrue((base / "logs" / "daemon.log").exists())
            self.assertEqual(logs["action"], "collect_logs")
            self.assertEqual(reveal["path"], str(config.sync_root))
            self.assertEqual(rebuilt["action"], "rebuild_cache")
            self.assertEqual((config.sync_root / "document.txt").read_text(encoding="utf-8"), "local")


if __name__ == "__main__":
    unittest.main()
