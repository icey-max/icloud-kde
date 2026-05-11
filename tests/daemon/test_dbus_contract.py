"""Tests for D-Bus contract constants and introspection XML."""

from __future__ import annotations

import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from icloud_kde.daemon import dbus  # noqa: E402


class DBusContractTests(unittest.TestCase):
    def _interface(self):
        root = ET.fromstring(dbus.INTROSPECTION_XML)
        return root.find("interface")

    def test_dbus_identity_constants(self) -> None:
        self.assertEqual(dbus.BUS_NAME, "org.kde.ICloudDrive")
        self.assertEqual(dbus.OBJECT_PATH, "/org/kde/ICloudDrive")
        self.assertEqual(dbus.INTERFACE_NAME, "org.kde.ICloudDrive")

    def test_dbus_xml_lists_required_methods(self) -> None:
        interface = self._interface()
        methods = {node.attrib["name"] for node in interface.findall("method")}

        self.assertEqual(
            methods,
            {
                "BeginSignIn",
                "CollectLogs",
                "GetAuthStatus",
                "GetStatus",
                "GetItemState",
                "GetConfig",
                "Hydrate",
                "ListProblemItems",
                "ListTrustedDevices",
                "Pause",
                "RebuildCache",
                "RequestReauth",
                "RequestSync",
                "Resume",
                "RevealSyncRoot",
                "SendTwoStepCode",
                "SetSyncRoot",
                "SubmitTwoFactorCode",
                "SubmitTwoStepCode",
            },
        )

    def test_dbus_xml_lists_required_signals(self) -> None:
        interface = self._interface()
        signals = {node.attrib["name"] for node in interface.findall("signal")}

        self.assertEqual(
            signals,
            {
                "StatusChanged",
                "ItemStateChanged",
                "ProgressChanged",
                "ProblemRaised",
                "AuthStateChanged",
                "RecoveryActionCompleted",
            },
        )

    def test_dbus_xml_begin_sign_in_uses_secret_reference(self) -> None:
        self.assertIn("BeginSignIn", dbus.INTROSPECTION_XML)
        self.assertIn("password_secret_ref", dbus.INTROSPECTION_XML)
        self.assertNotIn('name="password"', dbus.INTROSPECTION_XML)

    def test_dbus_xml_excludes_destructive_controls(self) -> None:
        names = dbus.INTROSPECTION_XML

        for forbidden in (
            "Shutdown",
            "Delete",
            "Purge",
            "Reset",
            "ForceOverwrite",
            "ResolveConflict",
            "ClearCache",
        ):
            self.assertNotIn(forbidden, names)


if __name__ == "__main__":
    unittest.main()
