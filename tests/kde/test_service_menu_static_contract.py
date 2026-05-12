"""Static contract tests for Phase 4 Dolphin file-item actions."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class ServiceMenuStaticContractTests(unittest.TestCase):
    def _read(self, relative: str) -> str:
        return (ROOT / relative).read_text(encoding="utf-8")

    def test_pathguard_is_part_of_shared_common_library(self) -> None:
        cmake = self._read("kde/common/CMakeLists.txt")
        header = self._read("kde/common/pathguard.h")
        source = self._read("kde/common/pathguard.cpp")

        self.assertIn("pathguard.cpp", cmake)
        self.assertIn("pathguard.h", cmake)
        for expected in [
            "PathGuard",
            "validateSelection",
            "canonicalFilePath",
            "isLocalFile",
            "sync_root",
            "relativePath",
        ]:
            self.assertIn(expected, header + source)

    def test_service_menu_target_uses_dynamic_kfileitemaction_plugin(self) -> None:
        root = self._read("kde/CMakeLists.txt")
        cmake = self._read("kde/service-menu/CMakeLists.txt")
        source = self._read("kde/service-menu/icloudfileitemaction.cpp")

        self.assertIn("add_subdirectory(service-menu)", root)
        self.assertIn("kcoreaddons_add_plugin(icloudfileitemaction", cmake)
        self.assertIn('INSTALL_NAMESPACE "kf6/kfileitemaction"', cmake)
        self.assertNotIn("kio/servicemenus", cmake)
        for expected in [
            "KAbstractFileItemActionPlugin",
            "KFileItemListProperties",
            "K_PLUGIN_CLASS_WITH_JSON",
            "actions(const KFileItemListProperties &fileItemInfos",
        ]:
            self.assertIn(expected, source)

    def test_service_menu_metadata_registers_icloud_drive_action_plugin(self) -> None:
        metadata = self._read("kde/service-menu/icloudfileitemaction.json")

        for expected in [
            '"Name": "iCloud Drive"',
            '"ServiceTypes"',
            '"KFileItemAction/Plugin"',
            '"MimeType"',
            '"application/octet-stream"',
            '"inode/directory"',
        ]:
            self.assertIn(expected, metadata)

    def test_actions_use_ui_spec_labels_icons_and_safe_daemon_methods(self) -> None:
        source = self._read("kde/service-menu/icloudfileitemaction.cpp")

        for expected in [
            "Open iCloud Folder",
            "Show iCloud Drive Status",
            "Pause iCloud Drive Sync",
            "Resume iCloud Drive Sync",
            "Show Conflict Details",
            "document-open-folder",
            "view-list-details",
            "media-playback-pause",
            "media-playback-start",
            "documentinfo",
            "RevealSyncRoot",
            "QDesktopServices::openUrl",
            "GetItemState",
            "ListProblemItems",
            "Pause",
            "Resume",
        ]:
            self.assertIn(expected, source)

    def test_actions_are_hidden_outside_sync_root_and_conflicts_are_conditional(self) -> None:
        source = self._read("kde/service-menu/icloudfileitemaction.cpp")

        for expected in [
            "PathGuard",
            "validateSelection",
            "return {};",
            "hasConflict",
            "conflicted",
            "Compare the conflict copy before deleting either version.",
        ]:
            self.assertIn(expected, source)

    def test_service_menu_avoids_private_state_destructive_actions_and_shells(self) -> None:
        combined = "\n".join(
            [
                self._read("kde/common/pathguard.cpp"),
                self._read("kde/service-menu/icloudfileitemaction.cpp"),
            ]
        ).lower()

        for forbidden in [
            "resolve conflict",
            "delete local",
            "force upload",
            "force download",
            "purge cache",
            "reset account",
            "/bin/sh",
            "sh -c",
            "sqlite",
            "journalctl",
            "pyicloud",
            "password",
            "token",
            "cookie",
            "secret_ref",
        ]:
            self.assertNotIn(forbidden, combined)


if __name__ == "__main__":
    unittest.main()
