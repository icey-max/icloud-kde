"""Static contract tests for the iCloud KCM."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class KCMStaticContractTests(unittest.TestCase):
    def _read(self, relative: str) -> str:
        return (ROOT / relative).read_text(encoding="utf-8")

    def test_kcm_metadata_declares_icloud_module(self) -> None:
        metadata = json.loads(self._read("kde/kcm/kcm_icloud.json"))

        self.assertEqual(metadata["KPlugin"]["Id"], "kcm_icloud")
        self.assertEqual(metadata["KPlugin"]["Name"], "iCloud Drive")
        self.assertEqual(metadata["KPlugin"]["Icon"], "folder-cloud")
        self.assertIn("icloud,drive,sync,apple,kwallet", metadata["X-KDE-Keywords"])

    def test_daemon_client_uses_stable_dbus_contract(self) -> None:
        source = self._read("kde/kcm/daemonclient.cpp")

        self.assertIn("org.kde.ICloudDrive", source)
        self.assertIn("/org/kde/ICloudDrive", source)
        self.assertIn("GetStatus", source)
        self.assertIn("GetAuthStatus", source)

    def test_daemon_client_exposes_auth_recovery_invokables(self) -> None:
        header = self._read("kde/kcm/daemonclient.h")

        for expected in [
            "refresh",
            "beginSignIn",
            "submitTwoFactorCode",
            "listTrustedDevices",
            "sendTwoStepCode",
            "submitTwoStepCode",
            "setSyncRoot",
            "requestReauth",
            "collectLogs",
            "rebuildCache",
            "revealSyncRoot",
            "passwordSecretRef",
        ]:
            self.assertIn(expected, header)

    def test_kcm_cmake_uses_qml_kcm_pattern(self) -> None:
        root = self._read("kde/CMakeLists.txt")
        cmake = self._read("kde/kcm/CMakeLists.txt")
        header = self._read("kde/kcm/icloudconfigmodule.h")
        source = self._read("kde/kcm/icloudconfigmodule.cpp")

        self.assertIn("add_subdirectory(kcm)", root)
        self.assertIn("kcmutils_add_qml_kcm(kcm_icloud)", cmake)
        self.assertIn("class ICloudConfigModule", header)
        self.assertIn('K_PLUGIN_CLASS_WITH_JSON(ICloudConfigModule, "kcm_icloud.json")', source)


if __name__ == "__main__":
    unittest.main()
