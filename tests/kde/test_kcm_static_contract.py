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

        self.assertNotIn("Id", metadata["KPlugin"])
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

    def test_account_page_contains_required_auth_states_and_copy(self) -> None:
        main = self._read("kde/kcm/ui/main.qml")
        account = self._read("kde/kcm/ui/AccountPage.qml")

        for page_name in ["AccountPage", "SyncPage", "RecoveryPage"]:
            self.assertIn(page_name, main)
        for expected in [
            "iCloud Drive is not connected",
            "Connect your Apple ID to choose a local sync folder and start syncing.",
            "Connect iCloud Drive",
            "iCloud needs attention. Review the account message, then reconnect or update recovery settings.",
            "Two-factor verification code",
            "Trusted device",
            "Reconnect",
            "beginSignIn",
            "submitTwoFactorCode",
            "sendTwoStepCode",
            "submitTwoStepCode",
            "daemonClient.authStatus.message || \"\"",
        ]:
            self.assertIn(expected, account)
        for state in [
            "signed_out",
            "needs_password",
            "authenticating",
            "needs_2fa",
            "needs_2sa_device",
            "needs_2sa_code",
            "trusted",
            "auth_required",
            "web_access_blocked",
            "account_blocked",
            "error",
        ]:
            self.assertIn(state, account)

    def test_kcm_starts_on_account_page_and_passes_daemon_client(self) -> None:
        main = self._read("kde/kcm/ui/main.qml")

        account_index = main.index("AccountPage")
        sync_index = main.index("SyncPage")
        recovery_index = main.index("RecoveryPage")

        self.assertLess(account_index, sync_index)
        self.assertLess(sync_index, recovery_index)
        self.assertIn("id: daemon", main)
        self.assertIn("currentIndex: pageTabs.currentIndex", main)
        self.assertNotIn("initialPage:", main)
        self.assertNotIn("push(syncPage)", main)
        self.assertNotIn("push(recoveryPage)", main)
        self.assertEqual(main.count("daemonClient: daemon"), 3)

    def test_sync_page_bounds_concurrency_to_safe_defaults(self) -> None:
        sync = self._read("kde/kcm/ui/SyncPage.qml")

        for expected in [
            "Sync root",
            "Cache location",
            "id: syncRoot",
            "id: cacheLocation",
            "id: startupBehavior",
            "id: warmupMode",
            "background",
            "lazy",
            "from: 1",
            "to: 3",
            "value: 1",
            "id: pauseOnStartup",
        ]:
            self.assertIn(expected, sync)

    def test_recovery_page_contains_required_actions_and_limitations(self) -> None:
        recovery = self._read("kde/kcm/ui/RecoveryPage.qml")

        for expected in [
            "Request re-authentication",
            "Reveal local folder",
            "Collect logs",
            "Rebuild cache",
            "Rebuild cache: Move the internal cache to a backup and rebuild it. Local files in the sync folder are not deleted.",
            "iCloud web access or account security settings can block Linux access.",
            "Advanced Data Protection may limit what this integration can read.",
            "Credentials and session material are stored in KWallet or a compatible secret-service backend, not plaintext project config.",
        ]:
            self.assertIn(expected, recovery)

    def test_daemon_client_cpp_contains_phase_three_dbus_methods(self) -> None:
        source = self._read("kde/kcm/daemonclient.cpp")

        for expected in [
            "GetStatus",
            "GetConfig",
            "SetSyncRoot",
            "GetAuthStatus",
            "BeginSignIn",
            "SubmitTwoFactorCode",
            "ListTrustedDevices",
            "SendTwoStepCode",
            "SubmitTwoStepCode",
            "RequestReauth",
            "CollectLogs",
            "RebuildCache",
            "RevealSyncRoot",
            "QDBusInterface",
        ]:
            self.assertIn(expected, source)

    def test_sync_and_recovery_pages_wire_required_actions(self) -> None:
        sync = self._read("kde/kcm/ui/SyncPage.qml")
        recovery = self._read("kde/kcm/ui/RecoveryPage.qml")

        for expected in [
            "id: syncRoot",
            "id: cacheLocation",
            "id: startupBehavior",
            "id: warmupMode",
            "id: concurrency",
            "id: pauseOnStartup",
            "daemonClient.setSyncRoot(syncRoot.text)",
        ]:
            self.assertIn(expected, sync)
        for expected in [
            "requestReauth",
            "revealSyncRoot",
            "collectLogs",
            "rebuildCache",
            "rebuild-cache",
            "id: rebuildCacheAcknowledgement",
            "rebuildCacheAcknowledgement.checked",
        ]:
            self.assertIn(expected, recovery)

    def test_user_setup_doc_contains_kcm_command_and_limitations(self) -> None:
        setup = self._read("docs/user/setup.md")

        for expected in [
            "## Open the iCloud Drive settings module",
            "## Connect your Apple ID",
            "## Choose sync locations",
            "## Recover from common problems",
            "## Privacy and security limits",
            "kcmshell6 kcm_icloud",
            "KWallet",
            "Advanced Data Protection",
            "not plaintext project config",
        ]:
            self.assertIn(expected, setup)


if __name__ == "__main__":
    unittest.main()
