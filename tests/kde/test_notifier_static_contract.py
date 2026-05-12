"""Static contract tests for Phase 4 KDE notifier integration."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class SharedDaemonClientStaticContractTests(unittest.TestCase):
    def _read(self, relative: str) -> str:
        return (ROOT / relative).read_text(encoding="utf-8")

    def test_common_client_is_registered_before_kde_clients(self) -> None:
        root = self._read("kde/CMakeLists.txt")
        common_index = root.index("add_subdirectory(common)")
        kcm_index = root.index("add_subdirectory(kcm)")

        self.assertLess(common_index, kcm_index)
        self.assertIn("add_library(icloud-kde-common STATIC", self._read("kde/common/CMakeLists.txt"))

    def test_common_daemon_client_uses_stable_dbus_identity(self) -> None:
        source = self._read("kde/common/daemonclient.cpp")

        self.assertIn("org.kde.ICloudDrive", source)
        self.assertIn("/org/kde/ICloudDrive", source)
        self.assertIn('QStringLiteral("org.kde.ICloudDrive")', source)

    def test_common_daemon_client_exposes_safe_methods(self) -> None:
        header = self._read("kde/common/daemonclient.h")
        source = self._read("kde/common/daemonclient.cpp")

        for expected in [
            "refresh",
            "getItemState",
            "pause",
            "resume",
            "requestSync",
            "hydrate",
            "requestReauth",
            "revealSyncRoot",
        ]:
            self.assertIn(expected, header)

        for method_name in [
            "GetStatus",
            "GetAuthStatus",
            "ListProblemItems",
            "GetConfig",
            "GetItemState",
            "Pause",
            "Resume",
            "RequestSync",
            "Hydrate",
            "RequestReauth",
            "RevealSyncRoot",
        ]:
            self.assertIn(method_name, source)

    def test_common_daemon_client_subscribes_to_dbus_signals(self) -> None:
        source = self._read("kde/common/daemonclient.cpp")

        self.assertIn("QDBusConnection::sessionBus().connect", source)
        for signal_name in [
            "StatusChanged",
            "ItemStateChanged",
            "ProgressChanged",
            "ProblemRaised",
            "AuthStateChanged",
            "RecoveryActionCompleted",
        ]:
            self.assertIn(signal_name, source)

    def test_common_daemon_client_has_bounded_polling_fallback(self) -> None:
        header = self._read("kde/common/daemonclient.h")
        source = self._read("kde/common/daemonclient.cpp")

        self.assertIn("QTimer", header)
        self.assertIn("QTimer", source)
        self.assertIn("startPolling", header)
        self.assertIn("stopPolling", header)
        self.assertIn("30000", source)
        self.assertIn("Snapshot", source)


if __name__ == "__main__":
    unittest.main()
