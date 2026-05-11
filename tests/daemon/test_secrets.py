"""Tests for daemon secret storage boundaries."""

from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from icloud_kde.daemon.config import DaemonConfig  # noqa: E402
from icloud_kde.daemon.secrets import (  # noqa: E402
    InMemorySecretStore,
    SecretKind,
    SubprocessSecretStore,
    build_secret_ref,
)


class FakeRunner:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def __call__(self, args: list[str], **kwargs: object) -> subprocess.CompletedProcess[bytes]:
        self.calls.append({"args": args, "kwargs": kwargs})
        command = args[1]
        stdout = b"stored-value" if command == "lookup" else b""
        return subprocess.CompletedProcess(args=args, returncode=0, stdout=stdout, stderr=b"")


class SecretStoreTests(unittest.TestCase):
    def test_secret_ref_uses_stable_service_namespace(self) -> None:
        ref = build_secret_ref("primary", SecretKind.APPLE_ID_PASSWORD)

        self.assertEqual(ref.service, "org.kde.ICloudDrive")
        self.assertEqual(ref.key(), "org.kde.ICloudDrive:primary:apple_id_password")

    def test_in_memory_secret_store_round_trips_bytes(self) -> None:
        ref = build_secret_ref("primary", "pyicloud_session")
        store = InMemorySecretStore()

        record = store.store(ref, b"session-bytes")

        self.assertTrue(record.stored)
        self.assertEqual(store.lookup(ref), b"session-bytes")
        self.assertTrue(store.delete(ref))
        self.assertIsNone(store.lookup(ref))

    def test_subprocess_secret_store_passes_store_value_on_stdin(self) -> None:
        runner = FakeRunner()
        store = SubprocessSecretStore(["icloud-kde-secret-tool"], runner=runner)
        ref = build_secret_ref("primary", SecretKind.APPLE_ID_PASSWORD)

        store.store(ref, b"raw-password")

        call = runner.calls[0]
        self.assertEqual(
            call["args"],
            [
                "icloud-kde-secret-tool",
                "store",
                "--account",
                "primary",
                "--kind",
                "apple_id_password",
            ],
        )
        self.assertEqual(call["kwargs"]["input"], b"raw-password")
        self.assertNotIn(b"raw-password", call["args"])

    def test_subprocess_secret_store_lookup_delete_and_status_commands(self) -> None:
        runner = FakeRunner()
        store = SubprocessSecretStore(["icloud-kde-secret-tool"], runner=runner)
        ref = build_secret_ref("primary", SecretKind.TRUST_METADATA)

        self.assertTrue(store.is_available())
        self.assertEqual(store.lookup(ref), b"stored-value")
        self.assertTrue(store.delete(ref))

        commands = [call["args"][1] for call in runner.calls]
        self.assertEqual(commands, ["status", "lookup", "delete"])

    def test_daemon_config_serialization_contains_no_secret_fields(self) -> None:
        text = str(DaemonConfig().to_dict()).lower()
        blocked = ["username", "password", "token", "cookie", "session", "secret"]

        self.assertFalse(any(word in text for word in blocked))


if __name__ == "__main__":
    unittest.main()
