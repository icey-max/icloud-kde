"""Daemon-owned authentication state and controller contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Protocol

from .secrets import SecretRef


class AuthState(str, Enum):
    SIGNED_OUT = "signed_out"
    NEEDS_PASSWORD = "needs_password"
    AUTHENTICATING = "authenticating"
    NEEDS_2FA = "needs_2fa"
    NEEDS_2SA_DEVICE = "needs_2sa_device"
    NEEDS_2SA_CODE = "needs_2sa_code"
    TRUSTED = "trusted"
    AUTH_REQUIRED = "auth_required"
    WEB_ACCESS_BLOCKED = "web_access_blocked"
    ACCOUNT_BLOCKED = "account_blocked"
    ERROR = "error"


class AuthProblemKind(str, Enum):
    INVALID_CREDENTIALS = "invalid_credentials"
    TWO_FACTOR_REQUIRED = "two_factor_required"
    TWO_STEP_REQUIRED = "two_step_required"
    WEB_ACCESS_BLOCKED = "web_access_blocked"
    ACCOUNT_BLOCKED = "account_blocked"
    NETWORK_ERROR = "network_error"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class TrustedDevice:
    device_id: str
    label: str
    delivery: str

    def to_dict(self) -> dict[str, object]:
        return {
            "device_id": self.device_id,
            "label": self.label,
            "delivery": self.delivery,
        }


@dataclass(frozen=True, slots=True)
class AuthStatus:
    state: AuthState
    account_label: str = "default"
    apple_id: str = ""
    problem_kind: AuthProblemKind | None = None
    message: str = ""
    devices: tuple[TrustedDevice, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "state": self.state.value,
            "account_label": self.account_label,
            "apple_id": self.apple_id,
            "problem_kind": self.problem_kind.value if self.problem_kind else "",
            "message": self.message,
            "devices": [device.to_dict() for device in self.devices],
        }


@dataclass(frozen=True, slots=True)
class AuthChallenge:
    state: AuthState
    message: str = ""
    devices: tuple[TrustedDevice, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "state": self.state.value,
            "message": self.message,
            "devices": [device.to_dict() for device in self.devices],
        }


class AuthController(Protocol):
    def begin_sign_in(self, apple_id: str, password_ref: SecretRef) -> AuthStatus:
        """Start sign-in using an existing password secret reference."""

    def submit_two_factor_code(self, code: str) -> AuthStatus:
        """Submit a two-factor code."""

    def list_trusted_devices(self) -> list[TrustedDevice]:
        """List trusted devices for a two-step challenge."""

    def send_two_step_code(self, device_id: str) -> AuthStatus:
        """Send a two-step code to a trusted device."""

    def submit_two_step_code(self, device_id: str, code: str) -> AuthStatus:
        """Submit a two-step verification code."""

    def trust_session(self) -> AuthStatus:
        """Trust the current authenticated session."""

    def sign_out(self) -> AuthStatus:
        """Forget the current auth state."""

    def get_status(self) -> AuthStatus:
        """Return current auth state."""


class FakeAuthController:
    """Deterministic auth controller for tests."""

    def __init__(
        self,
        account_label: str = "default",
        initial_state: AuthState = AuthState.SIGNED_OUT,
        requires_2fa: bool = False,
        requires_2sa: bool = False,
        problem_kind: AuthProblemKind | None = None,
    ) -> None:
        self.account_label = account_label
        self.requires_2fa = requires_2fa
        self.requires_2sa = requires_2sa
        self.apple_id = ""
        self.devices = [
            TrustedDevice(device_id="device-1", label="Trusted device", delivery="sms")
        ]
        self.status = AuthStatus(
            state=initial_state,
            account_label=account_label,
            problem_kind=problem_kind,
        )

    def begin_sign_in(self, apple_id: str, password_ref: SecretRef) -> AuthStatus:
        self.apple_id = apple_id
        if self.requires_2fa:
            return self._set(
                AuthState.NEEDS_2FA,
                AuthProblemKind.TWO_FACTOR_REQUIRED,
                "Two-factor authentication required.",
            )
        if self.requires_2sa:
            return self._set(
                AuthState.NEEDS_2SA_DEVICE,
                AuthProblemKind.TWO_STEP_REQUIRED,
                "Two-step authentication required.",
                tuple(self.devices),
            )
        return self._set(AuthState.TRUSTED, message="Authentication trusted.")

    def submit_two_factor_code(self, code: str) -> AuthStatus:
        if code == "123456":
            return self._set(AuthState.TRUSTED, message="Two-factor authentication complete.")
        return self._set(
            AuthState.ERROR,
            AuthProblemKind.INVALID_CREDENTIALS,
            "Invalid two-factor verification code.",
        )

    def list_trusted_devices(self) -> list[TrustedDevice]:
        return list(self.devices)

    def send_two_step_code(self, device_id: str) -> AuthStatus:
        if device_id != "device-1":
            return self._set(
                AuthState.ERROR,
                AuthProblemKind.UNKNOWN,
                "Trusted device not found.",
            )
        return self._set(
            AuthState.NEEDS_2SA_CODE,
            AuthProblemKind.TWO_STEP_REQUIRED,
            "Two-step verification code sent.",
            tuple(self.devices),
        )

    def submit_two_step_code(self, device_id: str, code: str) -> AuthStatus:
        if device_id == "device-1" and code == "654321":
            return self._set(AuthState.TRUSTED, message="Two-step authentication complete.")
        return self._set(
            AuthState.ERROR,
            AuthProblemKind.INVALID_CREDENTIALS,
            "Invalid two-step verification code.",
        )

    def trust_session(self) -> AuthStatus:
        return self._set(AuthState.TRUSTED, message="Session trusted.")

    def sign_out(self) -> AuthStatus:
        self.apple_id = ""
        return self._set(AuthState.SIGNED_OUT, message="Signed out.")

    def get_status(self) -> AuthStatus:
        return self.status

    def _set(
        self,
        state: AuthState,
        problem_kind: AuthProblemKind | None = None,
        message: str = "",
        devices: tuple[TrustedDevice, ...] = (),
    ) -> AuthStatus:
        self.status = AuthStatus(
            state=state,
            account_label=self.account_label,
            apple_id=self.apple_id,
            problem_kind=problem_kind,
            message=message,
            devices=devices,
        )
        return self.status
