"""Static contract tests for the KWallet helper."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class SecretToolStaticTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root_cmake = (ROOT / "CMakeLists.txt").read_text(encoding="utf-8")
        self.kde_cmake = (ROOT / "kde" / "CMakeLists.txt").read_text(encoding="utf-8")
        self.tool_cmake = (ROOT / "kde" / "secret-tool" / "CMakeLists.txt").read_text(
            encoding="utf-8"
        )
        self.source = (ROOT / "kde" / "secret-tool" / "main.cpp").read_text(
            encoding="utf-8"
        )

    def test_root_and_kde_cmake_include_secret_tool(self) -> None:
        self.assertIn("project(icloud-kde", self.root_cmake)
        self.assertIn("add_subdirectory(kde)", self.root_cmake)
        self.assertIn("add_subdirectory(secret-tool)", self.kde_cmake)

    def test_secret_tool_cmake_links_kwallet(self) -> None:
        self.assertIn("add_executable(icloud-kde-secret-tool", self.tool_cmake)
        self.assertIn("KF6::Wallet", self.tool_cmake)
        self.assertIn("KF6::I18n", self.tool_cmake)

    def test_secret_tool_source_uses_kwallet_namespace(self) -> None:
        for expected in [
            "KWallet::Wallet",
            "KWallet::Wallet::openWallet",
            "NetworkWallet",
            "iCloud KDE",
            "org.kde.ICloudDrive",
            "stdin",
        ]:
            self.assertIn(expected, self.source)

    def test_secret_tool_source_declares_required_commands(self) -> None:
        for command in ["status", "store", "lookup", "delete"]:
            self.assertIn(command, self.source)


if __name__ == "__main__":
    unittest.main()
