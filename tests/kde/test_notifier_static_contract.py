"""Static contract tests for Phase 4 KDE notifier integration."""

from __future__ import annotations

import sys
import unittest
import configparser
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


class NotifierStaticContractTests(unittest.TestCase):
    REQUIRED_EVENT_IDS = {
        "auth_required",
        "account_blocked",
        "conflict_created",
        "upload_stuck",
        "sync_paused",
        "sync_resumed",
        "hydration_completed",
    }

    def _read(self, relative: str) -> str:
        return (ROOT / relative).read_text(encoding="utf-8")

    def _notifyrc(self) -> configparser.ConfigParser:
        parser = configparser.ConfigParser()
        parser.optionxform = str
        parser.read_string(self._read("kde/notifier/icloud-kde.notifyrc"))
        return parser

    def test_notifier_cmake_links_required_kde_stack(self) -> None:
        root = self._read("kde/CMakeLists.txt")
        cmake = self._read("kde/notifier/CMakeLists.txt")

        self.assertIn("add_subdirectory(notifier)", root)
        self.assertIn("add_executable(icloud-kde-notifier", cmake)
        for expected in [
            "Qt::Core",
            "Qt::Widgets",
            "Qt::DBus",
            "KF6::I18n",
            "KF6::Notifications",
            "KF6::StatusNotifierItem",
            "icloud-kde-common",
        ]:
            self.assertIn(expected, cmake)
        self.assertIn("icloud-kde.notifyrc", cmake)
        self.assertIn("org.kde.icloud-drive.notifier.desktop", cmake)

    def test_notifier_main_owns_qapplication_and_policy(self) -> None:
        main = self._read("kde/notifier/main.cpp")

        self.assertIn("QApplication", main)
        self.assertIn("org.kde.icloud-drive.notifier", main)
        self.assertIn("runNotifier", main)

    def test_notifyrc_defines_exact_event_catalog(self) -> None:
        notifyrc = self._notifyrc()
        event_ids = {
            section.removeprefix("Event/")
            for section in notifyrc.sections()
            if section.startswith("Event/")
        }

        self.assertEqual(event_ids, self.REQUIRED_EVENT_IDS)
        self.assertEqual(notifyrc["Global"]["Name"], "iCloud Drive")
        self.assertEqual(notifyrc["Global"]["IconName"], "folder-cloud")
        self.assertEqual(
            notifyrc["Global"]["DesktopEntry"],
            "org.kde.icloud-drive.notifier.desktop",
        )

    def test_notifyrc_uses_ui_spec_titles_bodies_and_urgency(self) -> None:
        notifyrc = self._notifyrc()

        expected = {
            "auth_required": (
                "iCloud Drive needs sign-in",
                "Reconnect to resume syncing your iCloud Drive files.",
                "Critical",
            ),
            "account_blocked": (
                "iCloud Drive access is blocked",
                "Account security or iCloud web access settings are blocking Linux access.",
                "Critical",
            ),
            "conflict_created": (
                "iCloud Drive conflict saved",
                "A conflict copy was saved. Review it before deleting either version.",
                "Normal",
            ),
            "upload_stuck": (
                "iCloud Drive upload is stuck",
                "An item has not uploaded after repeated attempts. Review sync status.",
                "Normal",
            ),
            "sync_paused": (
                "iCloud Drive sync paused",
                "Local changes stay in the folder and will sync after resume.",
                "Low",
            ),
            "sync_resumed": (
                "iCloud Drive sync resumed",
                "New changes will sync in the background.",
                "Low",
            ),
            "hydration_completed": (
                "iCloud Drive file is ready",
                "The file is available locally.",
                "Low",
            ),
        }

        for event_id, (title, body, urgency) in expected.items():
            section = notifyrc[f"Event/{event_id}"]
            self.assertEqual(section["Name"], title)
            self.assertEqual(section["Comment"], body)
            self.assertEqual(section["Urgency"], urgency)
            self.assertIn("Popup", section["Action"])

    def test_notification_policy_uses_knotification_and_status_notifier(self) -> None:
        source = self._read("kde/notifier/notificationpolicy.cpp")

        for expected in [
            "KNotification",
            "KNotification::Persistent",
            "setComponentName",
            "KStatusNotifierItem",
            "KStatusNotifierItem::SystemServices",
            "setContextMenu",
            "setToolTip",
            "folder-cloud",
            "folder-sync",
            "dialog-error",
            "messagebox_warning",
            "iCloud Drive - Up to date",
            "iCloud Drive - Service unavailable",
        ]:
            self.assertIn(expected, source)
        self.assertNotIn("setIsMenu", source)

    def test_tray_menu_uses_ui_spec_order_and_safe_actions(self) -> None:
        source = self._read("kde/notifier/notificationpolicy.cpp")

        labels = [
            "iCloud Drive",
            "Open iCloud Folder",
            "Show Sync Status",
            "Sync Now",
            "Pause Sync",
            "Resume Sync",
            "Review Conflicts",
            "Reconnect iCloud Drive",
            "iCloud Drive Settings...",
        ]
        positions = [source.index(label) for label in labels]
        self.assertEqual(positions, sorted(positions))

        for expected in [
            "RevealSyncRoot",
            "RequestSync",
            "Pause",
            "Resume",
            "RequestReauth",
            "ListProblemItems",
            "kcmshell6",
            "kcm_icloud",
            "QProcess::startDetached",
        ]:
            self.assertIn(expected, source)

    def test_notification_policy_implements_coalescing_and_foreground_hydration(self) -> None:
        source = self._read("kde/notifier/notificationpolicy.cpp")

        for expected in [
            "Multiple iCloud Drive conflicts saved",
            "m_conflictWindow",
            "m_lastStuckUploadNotification",
            "30 * 60",
            "foreground_hydration",
            "hydration_completed",
            "auth_required",
            "account_blocked",
            "conflict_created",
            "upload_stuck",
            "sync_paused",
            "sync_resumed",
        ]:
            self.assertIn(expected, source)

    def test_notifier_runs_places_sync_hook_with_argument_list(self) -> None:
        source = self._read("kde/notifier/notificationpolicy.cpp")

        self.assertIn("icloud-kde-places", source)
        self.assertIn("--sync", source)
        self.assertIn("QProcess::startDetached", source)
        self.assertIn("sync_root", source)

    def test_notifier_copy_avoids_sensitive_or_destructive_surface(self) -> None:
        combined = "\n".join(
            [
                self._read("kde/notifier/notificationpolicy.cpp"),
                self._read("kde/notifier/icloud-kde.notifyrc"),
            ]
        ).lower()

        for forbidden in [
            "password",
            "token",
            "cookie",
            "secret_ref",
            "/home/",
            "delete",
            "purge",
            "reset",
            "force upload",
            "force download",
            "force overwrite",
            "resolve conflict",
        ]:
            self.assertNotIn(forbidden, combined)

    def test_desktop_file_uses_visible_icloud_drive_name(self) -> None:
        desktop = self._read("kde/notifier/org.kde.icloud-drive.notifier.desktop")

        self.assertIn("Name=iCloud Drive", desktop)
        self.assertIn("Exec=icloud-kde-notifier", desktop)
        self.assertIn("Icon=folder-cloud", desktop)


if __name__ == "__main__":
    unittest.main()
