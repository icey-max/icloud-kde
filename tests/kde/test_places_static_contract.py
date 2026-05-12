"""Static contract tests for Phase 4 Dolphin Places integration."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class PlacesStaticContractTests(unittest.TestCase):
    def _read(self, relative: str) -> str:
        return (ROOT / relative).read_text(encoding="utf-8")

    def test_places_target_is_registered_and_links_kde_places_stack(self) -> None:
        root = self._read("kde/CMakeLists.txt")
        cmake = self._read("kde/places/CMakeLists.txt")

        common_index = root.index("add_subdirectory(common)")
        places_index = root.index("add_subdirectory(places)")

        self.assertLess(common_index, places_index)
        self.assertIn("add_executable(icloud-kde-places", cmake)
        for expected in [
            "Qt::Core",
            "Qt::Widgets",
            "Qt::DBus",
            "KF6::I18n",
            "KF6::KIOFileWidgets",
            "icloud-kde-common",
        ]:
            self.assertIn(expected, cmake)

    def test_places_controller_uses_kfileplacesmodel_for_local_sync_root(self) -> None:
        source = self._read("kde/places/placescontroller.cpp")

        for expected in [
            "KFilePlacesModel",
            "bookmarkForUrl",
            "addPlace",
            "editPlace",
            "removePlace",
            "iCloud Drive",
            "folder-cloud",
            "QUrl::fromLocalFile",
            "GetConfig",
            "sync_root",
        ]:
            self.assertIn(expected, source)

    def test_places_helper_exposes_sync_and_cleanup_actions(self) -> None:
        main = self._read("kde/places/main.cpp")

        for expected in [
            "QApplication",
            "icloud-kde-places --sync",
            "--sync",
            "--remove",
            "syncFromDaemon",
            "removeProjectPlace",
        ]:
            self.assertIn(expected, main)

    def test_notifier_invokes_places_lifecycle_hook(self) -> None:
        notifier = self._read("kde/notifier/notificationpolicy.cpp")

        for expected in ["icloud-kde-places", "--sync", "QProcess"]:
            self.assertIn(expected, notifier)

    def test_places_avoids_manual_storage_and_virtual_urls(self) -> None:
        combined = "\n".join(
            [
                self._read("kde/places/main.cpp"),
                self._read("kde/places/placescontroller.cpp"),
            ]
        )

        self.assertNotIn("user-places.xbel", combined)
        self.assertNotIn("icloud:/", combined)
        for forbidden in ["sqlite", "journalctl", "pyicloud"]:
            self.assertNotIn(forbidden, combined.lower())

    def test_user_docs_describe_places_and_desktop_smoke_checks(self) -> None:
        setup = self._read("docs/user/setup.md")

        for expected in [
            "## Dolphin Places entry",
            "The Places entry is named `iCloud Drive`",
            "opens the local sync root",
            "## Phase 4 desktop smoke checks",
            "Places entry opens the local sync root",
            "kcmshell6 kcm_icloud",
        ]:
            self.assertIn(expected, setup)


if __name__ == "__main__":
    unittest.main()
