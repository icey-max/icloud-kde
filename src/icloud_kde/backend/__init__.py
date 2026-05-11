"""Backend adapter contracts for iCloud Drive sync."""

from .contract import (
    BackendCapabilities,
    BackendError,
    BackendErrorCode,
    BackendItem,
    BackendItemType,
    BackendSessionState,
    ICloudDriveBackendAdapter,
    RetryHint,
    UploadResult,
)

__all__ = [
    "BackendCapabilities",
    "BackendError",
    "BackendErrorCode",
    "BackendItem",
    "BackendItemType",
    "BackendSessionState",
    "ICloudDriveBackendAdapter",
    "RetryHint",
    "UploadResult",
]

