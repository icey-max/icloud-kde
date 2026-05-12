"""Transport-independent daemon status and control service."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Any, Mapping, Protocol

from .auth import AuthController, FakeAuthController
from .config import DaemonConfig, validate_sync_root
from .filesystem import scan_unsupported_entries
from .lifecycle import DaemonLifecycle
from .recovery import RecoveryController
from .secrets import DEFAULT_SECRET_SERVICE, SecretKind, SecretRef
from .state import (
    ItemState,
    ProblemItem,
    ProblemKind,
    ProblemSeverity,
    ProgressStatus,
    ServiceState,
    ServiceStatus,
    item_status_from_entry,
)

UNSUPPORTED_FILE_TYPE_KIND = "unsupported_file_type"


class StateRepository(Protocol):
    def get_entry(self, path: str) -> Mapping[str, Any] | None:
        """Return one durable state entry."""

    def list_entries(self) -> list[Mapping[str, Any]]:
        """Return all durable state entries."""

    def list_dirty_entries(self) -> list[Mapping[str, Any]]:
        """Return dirty or tombstoned durable state entries."""


class HydrationController(Protocol):
    def hydrate(self, path: str) -> None:
        """Hydrate a path if supported."""

    def request_sync(self) -> None:
        """Request a metadata or queue refresh."""

    def get_progress(self) -> Mapping[str, Any]:
        """Return current progress counters."""


class NullHydrationController:
    def hydrate(self, path: str) -> None:
        return None

    def request_sync(self) -> None:
        return None

    def get_progress(self) -> Mapping[str, Any]:
        return {}


class DaemonService:
    """Safe daemon API consumed by D-Bus and tests."""

    def __init__(
        self,
        lifecycle: DaemonLifecycle,
        repository: StateRepository | None = None,
        hydrator: HydrationController | None = None,
        service_state: ServiceState = ServiceState.IDLE,
        conflict_paths: set[str] | None = None,
        unsupported_paths: set[str] | None = None,
        syncing_paths: set[str] | None = None,
        stuck_upload_paths: set[str] | None = None,
        stuck_upload_metadata: Mapping[str, Mapping[str, Any]] | None = None,
        foreground_hydration_paths: set[str] | None = None,
        auth_controller: AuthController | None = None,
        recovery_controller: RecoveryController | None = None,
    ) -> None:
        self.lifecycle = lifecycle
        self.repository = repository
        self.hydrator = hydrator or NullHydrationController()
        self.auth_controller = auth_controller or FakeAuthController()
        self.recovery_controller = recovery_controller or RecoveryController(
            self.lifecycle.config or DaemonConfig()
        )
        self.service_state = service_state
        self.conflict_paths = conflict_paths or set()
        self.unsupported_paths = unsupported_paths or set()
        self.syncing_paths = syncing_paths or set()
        self.stuck_upload_paths = stuck_upload_paths or set()
        self.stuck_upload_metadata = dict(stuck_upload_metadata or {})
        self.foreground_hydration_paths = foreground_hydration_paths or set()

    def get_status(self) -> dict[str, object]:
        lifecycle_status = self.lifecycle.status()
        state = ServiceState.PAUSED if lifecycle_status.paused else self.service_state
        progress = dict(self.hydrator.get_progress())
        return ServiceStatus(
            state=state,
            sync_root=str(lifecycle_status.sync_root or ""),
            cache_dir=str(lifecycle_status.cache_dir or ""),
            paused=lifecycle_status.paused,
            message=lifecycle_status.message,
            progress=progress,
        ).to_dict()

    def get_item_state(self, path: str) -> dict[str, object]:
        entry = self.repository.get_entry(path) if self.repository else None
        status = item_status_from_entry(
            entry,
            service_state=self.service_state,
            syncing_paths=self.syncing_paths,
            conflict_paths=self.conflict_paths,
            unsupported_paths=self.unsupported_paths,
            requested_path=path,
        ).to_dict()
        if path in self.foreground_hydration_paths and status["state"] == ItemState.HYDRATED.value:
            status["foreground_hydration"] = True
            status["message"] = status["message"] or "File is available locally."
        return status

    def list_problem_items(self) -> list[dict[str, object]]:
        problems: list[ProblemItem] = []
        if self.repository:
            for entry in self.repository.list_dirty_entries():
                path = str(entry.get("path", ""))
                if self._entry_is_stuck_upload(path, entry):
                    problems.append(
                        ProblemItem(
                            path=path,
                            kind=ProblemKind.UPLOAD_STUCK,
                            severity=ProblemSeverity.WARNING,
                            state=ItemState.DIRTY,
                            message=(
                                f"{_safe_problem_name(path)} has not uploaded after "
                                "repeated attempts. Review sync status."
                            ),
                        )
                    )
                    continue
                problems.append(
                    ProblemItem(
                        path=path,
                        kind=ProblemKind.DIRTY,
                        severity=ProblemSeverity.INFO,
                        state=ItemState.DIRTY,
                        message="Local change is waiting to sync.",
                    )
                )

        blocker = _service_blocker_problem(self.service_state)
        if blocker is not None:
            problems.append(blocker)

        lifecycle_status = self.lifecycle.status()
        if lifecycle_status.sync_root:
            for entry in scan_unsupported_entries(lifecycle_status.sync_root):
                problems.append(
                    ProblemItem(
                        path=entry.path,
                        kind=ProblemKind(UNSUPPORTED_FILE_TYPE_KIND),
                        severity=ProblemSeverity.WARNING,
                        state=ItemState.UNSUPPORTED,
                        message=entry.reason or f"Unsupported file type: {entry.file_type}",
                    )
                )

        for path in sorted(self.conflict_paths):
            problems.append(
                ProblemItem(
                    path=path,
                    kind=ProblemKind.CONFLICT,
                    severity=ProblemSeverity.WARNING,
                    state=ItemState.CONFLICTED,
                    message="A conflict copy requires review before deleting either version.",
                )
            )

        return [problem.to_dict() for problem in problems]

    def _entry_is_stuck_upload(self, path: str, entry: Mapping[str, Any]) -> bool:
        if path in self.stuck_upload_paths:
            return True
        if bool(entry.get("upload_stuck")) or bool(entry.get("stuck_upload")):
            return True
        metadata = self.stuck_upload_metadata.get(path, {})
        return bool(metadata.get("stuck"))

    def pause(self) -> dict[str, object]:
        self.lifecycle.pause()
        return self.get_status()

    def resume(self) -> dict[str, object]:
        self.lifecycle.resume()
        return self.get_status()

    def request_sync(self) -> dict[str, object]:
        self.hydrator.request_sync()
        self.service_state = ServiceState.SYNCING
        return self.get_status()

    def hydrate(self, path: str) -> dict[str, object]:
        self.hydrator.hydrate(path)
        self.syncing_paths.add(path)
        return self.get_item_state(path)

    def get_config(self) -> dict[str, object]:
        config = self.lifecycle.config
        return config.to_dict() if config else DaemonConfig().to_dict()

    def set_sync_root(self, path: str) -> dict[str, object]:
        config = self.lifecycle.config or DaemonConfig()
        sync_root = validate_sync_root(path, config.cache_dir, create=True)
        updated = replace(config, sync_root=sync_root)
        self.lifecycle.configure(updated)
        return self.get_config()

    def get_auth_status(self) -> dict[str, object]:
        return self.auth_controller.get_status().to_dict()

    def begin_sign_in(self, apple_id: str, password_secret_ref: str) -> dict[str, object]:
        ref = _parse_password_secret_ref(password_secret_ref)
        return self.auth_controller.begin_sign_in(apple_id, ref).to_dict()

    def submit_two_factor_code(self, code: str) -> dict[str, object]:
        return self.auth_controller.submit_two_factor_code(code).to_dict()

    def list_trusted_devices(self) -> list[dict[str, object]]:
        return [device.to_dict() for device in self.auth_controller.list_trusted_devices()]

    def send_two_step_code(self, device_id: str) -> dict[str, object]:
        return self.auth_controller.send_two_step_code(device_id).to_dict()

    def submit_two_step_code(self, device_id: str, code: str) -> dict[str, object]:
        return self.auth_controller.submit_two_step_code(device_id, code).to_dict()

    def request_reauth(self) -> dict[str, object]:
        self.auth_controller.sign_out()
        return self.recovery_controller.request_reauth().to_dict()

    def collect_logs(self, destination: str) -> dict[str, object]:
        return self.recovery_controller.collect_logs(destination).to_dict()

    def rebuild_cache(self, confirm_token: str) -> dict[str, object]:
        return self.recovery_controller.execute_cache_rebuild(confirm_token).to_dict()

    def reveal_sync_root(self) -> dict[str, object]:
        return self.recovery_controller.reveal_sync_root().to_dict()


def _parse_password_secret_ref(value: str) -> SecretRef:
    parts = value.split(":")
    if len(parts) != 3:
        raise ValueError("password_secret_ref must be org.kde.ICloudDrive:<account>:<kind>")
    service, account_label, kind = parts
    if service != DEFAULT_SECRET_SERVICE:
        raise ValueError("password_secret_ref service must be org.kde.ICloudDrive")
    if kind != SecretKind.APPLE_ID_PASSWORD.value:
        raise ValueError("password_secret_ref kind must be apple_id_password")
    return SecretRef(account_label=account_label, kind=SecretKind.APPLE_ID_PASSWORD)


def _safe_problem_name(path: str) -> str:
    name = Path(path).name or "This item"
    if "@" in name:
        return "This item"
    return name


def _service_blocker_problem(state: ServiceState) -> ProblemItem | None:
    if state is ServiceState.AUTH_REQUIRED:
        return ProblemItem(
            path="",
            kind=ProblemKind.AUTH_REQUIRED,
            severity=ProblemSeverity.ERROR,
            state=ItemState.AUTH_REQUIRED,
            message="Reconnect iCloud Drive to resume syncing.",
        )
    if state is ServiceState.ACCOUNT_BLOCKED:
        return ProblemItem(
            path="",
            kind=ProblemKind.ACCOUNT_BLOCKED,
            severity=ProblemSeverity.ERROR,
            state=ItemState.AUTH_REQUIRED,
            message="Account security settings are blocking Linux access.",
        )
    if state is ServiceState.WEB_ACCESS_BLOCKED:
        return ProblemItem(
            path="",
            kind=ProblemKind.WEB_ACCESS_BLOCKED,
            severity=ProblemSeverity.ERROR,
            state=ItemState.AUTH_REQUIRED,
            message="iCloud web access settings are blocking Linux access.",
        )
    return None
