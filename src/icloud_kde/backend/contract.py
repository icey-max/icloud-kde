"""Project-owned iCloud Drive backend adapter contract.

This module deliberately uses only standard-library types. It is the boundary
that later daemon and KDE-facing code consume, so backend library objects and
session internals must stay behind adapter implementations.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping, Protocol, Sequence


class BackendItemType(str, Enum):
    """Supported iCloud Drive item kinds for v1 sync semantics."""

    FILE = "file"
    FOLDER = "folder"


class BackendErrorCode(str, Enum):
    """Stable backend error categories exposed above the adapter boundary."""

    AUTH_REQUIRED = "auth_required"
    ACCOUNT_BLOCKED = "account_blocked"
    WEB_ACCESS_BLOCKED = "web_access_blocked"
    THROTTLED = "throttled"
    TRANSIENT_NETWORK = "transient_network"
    NOT_FOUND = "not_found"
    PRECONDITION_CONFLICT = "precondition_conflict"
    UNSUPPORTED_RESPONSE = "unsupported_response"
    CONTRACT_MISMATCH = "contract_mismatch"


@dataclass(slots=True)
class RetryHint:
    """Adapter hint for retryable backend failures."""

    retryable: bool = False
    delay_seconds: int | None = None
    reason: str | None = None


@dataclass(slots=True)
class BackendError(Exception):
    """Normalized backend exception raised by adapter implementations."""

    code: BackendErrorCode
    message: str
    retry_hint: RetryHint = field(default_factory=RetryHint)

    def __post_init__(self) -> None:
        super().__init__(f"{self.code.value}: {self.message}")


@dataclass(frozen=True, slots=True)
class BackendCapabilities:
    """Backend features that the sync engine can rely on."""

    supports_upload: bool = True
    supports_rename: bool = True
    supports_move: bool = True
    supports_delete: bool = True
    supports_shared_metadata: bool = True
    max_parallel_downloads: int = 1
    max_parallel_uploads: int = 1


@dataclass(frozen=True, slots=True)
class BackendSessionState:
    """Current authentication and account-access state."""

    authenticated: bool
    requires_2fa: bool = False
    requires_2sa: bool = False
    account_blocked: bool = False
    web_access_blocked: bool = False
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class BackendItem:
    """Normalized iCloud Drive item metadata."""

    path: str
    name: str
    item_type: BackendItemType
    remote_drivewsid: str
    parent_drivewsid: str | None = None
    parent_path: str | None = None
    remote_docwsid: str | None = None
    remote_etag: str | None = None
    remote_zone: str | None = None
    remote_shareid: Mapping[str, Any] | str | None = None
    size: int = 0
    mtime: int = 0
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class UploadResult:
    """Result of an upload or replace operation."""

    item: BackendItem
    created: bool
    replaced: bool = False


class ICloudDriveBackendAdapter(Protocol):
    """Sync-facing adapter boundary for iCloud Drive operations."""

    def get_capabilities(self) -> BackendCapabilities:
        """Return feature and concurrency limits for this backend."""

    def validate_session(self) -> BackendSessionState:
        """Return current session/access state without exposing secrets."""

    def list_tree(self, root_drivewsid: str | None = None) -> Sequence[BackendItem]:
        """Return normalized metadata for descendants under a backend root."""

    def get_item_metadata(
        self,
        remote_drivewsid: str,
        remote_shareid: Mapping[str, Any] | str | None = None,
    ) -> BackendItem:
        """Return normalized metadata for one backend item."""

    def download_file(self, item: BackendItem) -> bytes:
        """Download file bytes for a normalized backend item."""

    def upload_file(
        self,
        parent_drivewsid: str,
        name: str,
        content: bytes,
        *,
        replace_drivewsid: str | None = None,
    ) -> UploadResult:
        """Upload a new file or replace an existing backend item."""

    def create_folder(self, parent_drivewsid: str, name: str) -> BackendItem:
        """Create a folder under a backend parent."""

    def rename_item(
        self,
        remote_drivewsid: str,
        new_name: str,
        remote_shareid: Mapping[str, Any] | str | None = None,
    ) -> BackendItem:
        """Rename an item and return refreshed metadata."""

    def move_item(
        self,
        remote_drivewsid: str,
        destination_parent_drivewsid: str,
        remote_shareid: Mapping[str, Any] | str | None = None,
    ) -> BackendItem:
        """Move an item to another backend parent and return metadata."""

    def delete_item(
        self,
        remote_drivewsid: str,
        remote_shareid: Mapping[str, Any] | str | None = None,
    ) -> None:
        """Delete or trash an item."""

    def get_shared_metadata(
        self,
        remote_drivewsid: str,
        remote_shareid: Mapping[str, Any] | str | None = None,
    ) -> Mapping[str, Any]:
        """Return shared-item metadata without exposing backend internals."""

