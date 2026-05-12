"""Static contract tests for Phase 4 Baloo integration."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class BalooStaticContractTests(unittest.TestCase):
    def _read(self, relative: str) -> str:
        return (ROOT / relative).read_text(encoding="utf-8")

    def test_baloo_target_is_registered_and_builds_controller(self) -> None:
        root = self._read("kde/CMakeLists.txt")
        cmake = self._read("kde/baloo/CMakeLists.txt")

        self.assertIn("add_subdirectory(baloo)", root)
        self.assertIn("add_executable(icloud-kde-baloo", cmake)
        self.assertIn("baloocontroller.cpp", cmake)
        self.assertIn("icloud-kde-common", cmake)

    def test_baloo_controller_uses_daemon_config_and_runtime_gate(self) -> None:
        source = self._read("kde/baloo/baloocontroller.cpp")

        for expected in [
            "GetConfig",
            "GetItemState",
            "Baloo::IndexerConfig",
            "balooctl6",
            "balooshow6",
            "baloosearch6",
            "root_not_configured",
            "hydrated_enabled",
            "placeholders_name_only",
            "disabled_by_user",
            "error",
        ]:
            self.assertIn(expected, source)

    def test_baloo_copy_matches_ui_spec(self) -> None:
        combined = "\n".join(
            [
                self._read("kde/baloo/baloocontroller.cpp"),
                self._read("docs/user/setup.md"),
            ]
        )

        for expected in [
            "Search indexing",
            "Hydrated files in your iCloud Drive folder can appear in KDE search.",
            "Remote-only placeholders are indexed by name only until they download.",
            "KDE file indexing is disabled for this folder. You can still browse files in Dolphin.",
            "Indexing status is unavailable. Check the sync folder in iCloud Drive settings.",
        ]:
            self.assertIn(expected, combined)

    def test_baloo_privacy_exclusions_and_no_remote_search_claims(self) -> None:
        combined = "\n".join(
            [
                self._read("kde/baloo/baloocontroller.cpp"),
                self._read("docs/developer/daemon-api.md"),
                self._read("tests/kde/test_baloo_static_contract.py"),
            ]
        )
        lower = combined.lower()

        for expected in ["cache", "sqlite", "logs", "cookies", "tokens", "kwallet"]:
            self.assertIn(expected, lower)
        for forbidden in [
            "apple-side search",
            "remote content search",
            "actual password",
            "raw password",
            "session token",
            "auth token",
            "cookie value",
            "secret value",
        ]:
            self.assertNotIn(forbidden, lower)


if __name__ == "__main__":
    unittest.main()
