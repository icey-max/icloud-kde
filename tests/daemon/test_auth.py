"""Tests for daemon auth state controllers."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from icloud_kde.daemon.auth import (  # noqa: E402
    AuthProblemKind,
    AuthState,
    AuthStatus,
    FakeAuthController,
)
from icloud_kde.daemon.secrets import SecretKind, build_secret_ref  # noqa: E402


class AuthControllerTests(unittest.TestCase):
    def test_auth_status_to_dict_excludes_secret_values(self) -> None:
        status = AuthStatus(
            state=AuthState.TRUSTED,
            account_label="primary",
            apple_id="jane@example.com",
            problem_kind=AuthProblemKind.UNKNOWN,
            message="ok",
        ).to_dict()

        text = str(status).lower()
        for forbidden in ["password", "token", "cookie", "session", "secret"]:
            self.assertNotIn(forbidden, text)

    def test_fake_auth_controller_signs_in_without_challenge(self) -> None:
        controller = FakeAuthController()
        ref = build_secret_ref("default", SecretKind.APPLE_ID_PASSWORD)

        status = controller.begin_sign_in("jane@example.com", ref)

        self.assertEqual(status.state, AuthState.TRUSTED)
        self.assertEqual(status.apple_id, "jane@example.com")

    def test_fake_auth_controller_two_factor_flow(self) -> None:
        controller = FakeAuthController(requires_2fa=True)
        ref = build_secret_ref("default", SecretKind.APPLE_ID_PASSWORD)

        challenge = controller.begin_sign_in("jane@example.com", ref)
        bad = controller.submit_two_factor_code("000000")
        good = controller.submit_two_factor_code("123456")

        self.assertEqual(challenge.state, AuthState.NEEDS_2FA)
        self.assertEqual(challenge.problem_kind, AuthProblemKind.TWO_FACTOR_REQUIRED)
        self.assertEqual(bad.problem_kind, AuthProblemKind.INVALID_CREDENTIALS)
        self.assertEqual(good.state, AuthState.TRUSTED)

    def test_fake_auth_controller_two_step_flow(self) -> None:
        controller = FakeAuthController(requires_2sa=True)
        ref = build_secret_ref("default", SecretKind.APPLE_ID_PASSWORD)

        challenge = controller.begin_sign_in("jane@example.com", ref)
        sent = controller.send_two_step_code("device-1")
        trusted = controller.submit_two_step_code("device-1", "654321")

        self.assertEqual(challenge.state, AuthState.NEEDS_2SA_DEVICE)
        self.assertEqual(challenge.devices[0].device_id, "device-1")
        self.assertEqual(sent.state, AuthState.NEEDS_2SA_CODE)
        self.assertEqual(trusted.state, AuthState.TRUSTED)

    def test_auth_states_include_web_and_account_blockers(self) -> None:
        values = {state.value for state in AuthState}

        self.assertIn("web_access_blocked", values)
        self.assertIn("account_blocked", values)
        self.assertIn("auth_required", values)


if __name__ == "__main__":
    unittest.main()
