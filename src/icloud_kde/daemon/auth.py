"""Daemon-owned authentication state and controller contracts."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Protocol

from .secrets import SecretRef, SecretStore


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


class PyiCloudAuthController:
    """pyicloud-backed controller isolated behind project-owned DTOs."""

    def __init__(
        self,
        account_label: str,
        secret_store: SecretStore,
        cookie_dir: Path,
        service_factory: Callable[..., object] | None = None,
    ) -> None:
        self.account_label = account_label
        self.secret_store = secret_store
        self.cookie_dir = cookie_dir
        self.service_factory = service_factory or self._default_service_factory
        self.apple_id = ""
        self.api: object | None = None
        self.status = AuthStatus(state=AuthState.SIGNED_OUT, account_label=account_label)

    def begin_sign_in(self, apple_id: str, password_ref: SecretRef) -> AuthStatus:
        self.apple_id = apple_id
        password_bytes = self.secret_store.lookup(password_ref)
        if password_bytes is None:
            return self._set(
                AuthState.NEEDS_PASSWORD,
                AuthProblemKind.INVALID_CREDENTIALS,
                "Password secret reference could not be resolved.",
            )

        password = password_bytes.decode("utf-8")
        try:
            self.api = self.service_factory(
                apple_id,
                password,
                cookie_directory=str(self.cookie_dir),
            )
        except Exception as exc:  # pragma: no cover - exercised with fake exceptions
            return self._status_from_exception(exc)
        finally:
            password = ""

        if bool(getattr(self.api, "requires_2fa", False)):
            requester = getattr(self.api, "request_2fa_code", None)
            if callable(requester):
                requester()
            return self._set(
                AuthState.NEEDS_2FA,
                AuthProblemKind.TWO_FACTOR_REQUIRED,
                "Two-factor authentication required.",
            )
        if bool(getattr(self.api, "requires_2sa", False)):
            return self._set(
                AuthState.NEEDS_2SA_DEVICE,
                AuthProblemKind.TWO_STEP_REQUIRED,
                "Two-step authentication required.",
                tuple(self.list_trusted_devices()),
            )
        return self._set(AuthState.TRUSTED, message="Authentication trusted.")

    def submit_two_factor_code(self, code: str) -> AuthStatus:
        if self.api is None:
            return self._set(AuthState.AUTH_REQUIRED, message="Sign in before submitting a code.")
        validator = getattr(self.api, "validate_2fa_code", None)
        if not callable(validator) or not validator(code):
            return self._set(
                AuthState.ERROR,
                AuthProblemKind.INVALID_CREDENTIALS,
                "Invalid two-factor verification code.",
            )
        if not bool(getattr(self.api, "is_trusted_session", True)):
            trustee = getattr(self.api, "trust_session", None)
            if callable(trustee):
                trustee()
        return self._set(AuthState.TRUSTED, message="Two-factor authentication complete.")

    def list_trusted_devices(self) -> list[TrustedDevice]:
        if self.api is None:
            return []
        raw_devices = list(getattr(self.api, "trusted_devices", []) or [])
        return [self._trusted_device(index, device) for index, device in enumerate(raw_devices)]

    def send_two_step_code(self, device_id: str) -> AuthStatus:
        device = self._raw_device(device_id)
        if self.api is None or device is None:
            return self._set(
                AuthState.ERROR,
                AuthProblemKind.UNKNOWN,
                "Trusted device not found.",
            )
        sender = getattr(self.api, "send_verification_code", None)
        if not callable(sender) or not sender(device):
            return self._set(AuthState.ERROR, AuthProblemKind.UNKNOWN, "Failed to send code.")
        return self._set(
            AuthState.NEEDS_2SA_CODE,
            AuthProblemKind.TWO_STEP_REQUIRED,
            "Two-step verification code sent.",
            tuple(self.list_trusted_devices()),
        )

    def submit_two_step_code(self, device_id: str, code: str) -> AuthStatus:
        device = self._raw_device(device_id)
        if self.api is None or device is None:
            return self._set(
                AuthState.ERROR,
                AuthProblemKind.UNKNOWN,
                "Trusted device not found.",
            )
        validator = getattr(self.api, "validate_verification_code", None)
        if not callable(validator) or not validator(device, code):
            return self._set(
                AuthState.ERROR,
                AuthProblemKind.INVALID_CREDENTIALS,
                "Invalid two-step verification code.",
            )
        return self._set(AuthState.TRUSTED, message="Two-step authentication complete.")

    def trust_session(self) -> AuthStatus:
        if self.api is None:
            return self._set(AuthState.AUTH_REQUIRED, message="No active session to trust.")
        trustee = getattr(self.api, "trust_session", None)
        if callable(trustee) and not trustee():
            return self._set(AuthState.ERROR, AuthProblemKind.UNKNOWN, "Session trust failed.")
        return self._set(AuthState.TRUSTED, message="Session trusted.")

    def sign_out(self) -> AuthStatus:
        logout = getattr(self.api, "logout", None)
        if callable(logout):
            logout()
        self.api = None
        self.apple_id = ""
        return self._set(AuthState.SIGNED_OUT, message="Signed out.")

    def get_status(self) -> AuthStatus:
        return self.status

    @staticmethod
    def _default_service_factory(*args: object, **kwargs: object) -> object:
        from pyicloud import PyiCloudService

        return PyiCloudService(*args, **kwargs)

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

    def _status_from_exception(self, exc: Exception) -> AuthStatus:
        text = str(exc).lower()
        name = exc.__class__.__name__.lower()
        if "failedlogin" in name or "invalid" in text or "credential" in text:
            return self._set(
                AuthState.NEEDS_PASSWORD,
                AuthProblemKind.INVALID_CREDENTIALS,
                "Invalid Apple ID credentials.",
            )
        if (
            "terms" in text
            or "web access" in text
            or "advanced data protection" in text
            or "adp" in text
        ):
            return self._set(
                AuthState.WEB_ACCESS_BLOCKED,
                AuthProblemKind.WEB_ACCESS_BLOCKED,
                str(exc),
            )
        if "blocked" in text or "locked" in text or "disabled" in text:
            return self._set(
                AuthState.ACCOUNT_BLOCKED,
                AuthProblemKind.ACCOUNT_BLOCKED,
                str(exc),
            )
        if "network" in text or "timeout" in text or "connection" in text:
            return self._set(AuthState.ERROR, AuthProblemKind.NETWORK_ERROR, str(exc))
        return self._set(AuthState.ERROR, AuthProblemKind.UNKNOWN, str(exc))

    def _trusted_device(self, index: int, device: object) -> TrustedDevice:
        if isinstance(device, dict):
            label = str(device.get("deviceName") or f"SMS to {device.get('phoneNumber', 'unknown')}")
            delivery = "sms" if device.get("phoneNumber") else "device"
            device_id = str(device.get("id") or device.get("deviceId") or f"device-{index + 1}")
            return TrustedDevice(device_id=device_id, label=label, delivery=delivery)
        return TrustedDevice(
            device_id=f"device-{index + 1}",
            label=str(device),
            delivery="device",
        )

    def _raw_device(self, device_id: str) -> object | None:
        if self.api is None:
            return None
        raw_devices = list(getattr(self.api, "trusted_devices", []) or [])
        for index, device in enumerate(raw_devices):
            if self._trusted_device(index, device).device_id == device_id:
                return device
        return None
