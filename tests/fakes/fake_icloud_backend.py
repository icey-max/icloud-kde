"""Deterministic in-memory implementation of the backend adapter contract."""

from __future__ import annotations

import posixpath
import time
from dataclasses import replace
from typing import Any, Mapping

from icloud_kde.backend.contract import (
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


class FakeICloudDriveBackend(ICloudDriveBackendAdapter):
    """Small synthetic iCloud Drive tree for contract and sync tests."""

    def __init__(self) -> None:
        self._counter = 0
        self._items: dict[str, BackendItem] = {
            "root": BackendItem(
                path="/",
                name="root",
                item_type=BackendItemType.FOLDER,
                remote_drivewsid="root",
                parent_drivewsid=None,
                parent_path=None,
                size=0,
                mtime=0,
            )
        }
        self._content: dict[str, bytes] = {}
        self._errors: dict[str, BackendError] = {}
        self._session = BackendSessionState(authenticated=True)
        self._capabilities = BackendCapabilities()

    def inject_error(
        self,
        method_name: str,
        error: BackendError | None = None,
    ) -> None:
        self._errors[method_name] = error or BackendError(
            BackendErrorCode.TRANSIENT_NETWORK,
            f"Injected failure for {method_name}",
            RetryHint(retryable=True, delay_seconds=5, reason="injected"),
        )

    def seed_folder(
        self,
        path: str,
        *,
        remote_shareid: Mapping[str, Any] | str | None = None,
    ) -> BackendItem:
        parent = self._ensure_parent_path(posixpath.dirname(path) or "/")
        return self._create_item(
            parent.remote_drivewsid,
            posixpath.basename(path),
            BackendItemType.FOLDER,
            b"",
            remote_shareid=remote_shareid,
        )

    def seed_file(
        self,
        path: str,
        content: bytes,
        *,
        remote_shareid: Mapping[str, Any] | str | None = None,
    ) -> BackendItem:
        parent = self._ensure_parent_path(posixpath.dirname(path) or "/")
        return self._create_item(
            parent.remote_drivewsid,
            posixpath.basename(path),
            BackendItemType.FILE,
            content,
            remote_shareid=remote_shareid,
        )

    def get_capabilities(self) -> BackendCapabilities:
        self._maybe_raise("get_capabilities")
        return self._capabilities

    def validate_session(self) -> BackendSessionState:
        self._maybe_raise("validate_session")
        return self._session

    def list_tree(self, root_drivewsid: str | None = None) -> list[BackendItem]:
        self._maybe_raise("list_tree")
        root_id = root_drivewsid or "root"
        root = self._require_item(root_id)
        root_prefix = "/" if root.path == "/" else root.path.rstrip("/") + "/"
        return sorted(
            [
                item
                for item in self._items.values()
                if item.remote_drivewsid != root_id
                and (root.path == "/" or item.path.startswith(root_prefix))
            ],
            key=lambda item: item.path,
        )

    def get_item_metadata(
        self,
        remote_drivewsid: str,
        remote_shareid: Mapping[str, Any] | str | None = None,
    ) -> BackendItem:
        self._maybe_raise("get_item_metadata")
        item = self._require_item(remote_drivewsid)
        if remote_shareid is not None and item.remote_shareid != remote_shareid:
            raise BackendError(
                BackendErrorCode.NOT_FOUND,
                f"Shared item {remote_drivewsid} not found for share id",
            )
        return item

    def download_file(self, item: BackendItem) -> bytes:
        self._maybe_raise("download_file")
        current = self._require_item(item.remote_drivewsid)
        if current.item_type != BackendItemType.FILE:
            raise BackendError(
                BackendErrorCode.CONTRACT_MISMATCH,
                f"{current.remote_drivewsid} is not a file",
            )
        return self._content[current.remote_drivewsid]

    def upload_file(
        self,
        parent_drivewsid: str,
        name: str,
        content: bytes,
        *,
        replace_drivewsid: str | None = None,
    ) -> UploadResult:
        self._maybe_raise("upload_file")
        if replace_drivewsid:
            item = self._require_item(replace_drivewsid)
            if item.item_type != BackendItemType.FILE:
                raise BackendError(
                    BackendErrorCode.CONTRACT_MISMATCH,
                    f"{replace_drivewsid} is not a file",
                )
            updated = replace(
                item,
                name=name,
                size=len(content),
                mtime=self._now(),
                remote_etag=self._new_etag(item.remote_drivewsid),
            )
            self._items[item.remote_drivewsid] = updated
            self._content[item.remote_drivewsid] = content
            return UploadResult(updated, created=False, replaced=True)

        item = self._create_item(parent_drivewsid, name, BackendItemType.FILE, content)
        return UploadResult(item, created=True, replaced=False)

    def create_folder(self, parent_drivewsid: str, name: str) -> BackendItem:
        self._maybe_raise("create_folder")
        return self._create_item(parent_drivewsid, name, BackendItemType.FOLDER, b"")

    def rename_item(
        self,
        remote_drivewsid: str,
        new_name: str,
        remote_shareid: Mapping[str, Any] | str | None = None,
    ) -> BackendItem:
        self._maybe_raise("rename_item")
        item = self.get_item_metadata(remote_drivewsid, remote_shareid)
        parent_path = item.parent_path or "/"
        new_path = self._join_path(parent_path, new_name)
        return self._relocate_subtree(item, new_path, new_name, item.parent_drivewsid)

    def move_item(
        self,
        remote_drivewsid: str,
        destination_parent_drivewsid: str,
        remote_shareid: Mapping[str, Any] | str | None = None,
    ) -> BackendItem:
        self._maybe_raise("move_item")
        item = self.get_item_metadata(remote_drivewsid, remote_shareid)
        destination = self._require_item(destination_parent_drivewsid)
        if destination.item_type != BackendItemType.FOLDER:
            raise BackendError(
                BackendErrorCode.CONTRACT_MISMATCH,
                f"{destination_parent_drivewsid} is not a folder",
            )
        new_path = self._join_path(destination.path, item.name)
        return self._relocate_subtree(
            item,
            new_path,
            item.name,
            destination.remote_drivewsid,
        )

    def delete_item(
        self,
        remote_drivewsid: str,
        remote_shareid: Mapping[str, Any] | str | None = None,
    ) -> None:
        self._maybe_raise("delete_item")
        item = self.get_item_metadata(remote_drivewsid, remote_shareid)
        ids_to_delete = [
            current.remote_drivewsid
            for current in self._items.values()
            if current.remote_drivewsid == item.remote_drivewsid
            or current.path.startswith(item.path.rstrip("/") + "/")
        ]
        for item_id in ids_to_delete:
            self._items.pop(item_id, None)
            self._content.pop(item_id, None)

    def get_shared_metadata(
        self,
        remote_drivewsid: str,
        remote_shareid: Mapping[str, Any] | str | None = None,
    ) -> Mapping[str, Any]:
        self._maybe_raise("get_shared_metadata")
        item = self.get_item_metadata(remote_drivewsid, remote_shareid)
        return {
            "remote_drivewsid": item.remote_drivewsid,
            "remote_shareid": item.remote_shareid,
            "path": item.path,
        }

    def _maybe_raise(self, method_name: str) -> None:
        error = self._errors.pop(method_name, None)
        if error:
            raise error

    def _require_item(self, remote_drivewsid: str) -> BackendItem:
        try:
            return self._items[remote_drivewsid]
        except KeyError as exc:
            raise BackendError(
                BackendErrorCode.NOT_FOUND,
                f"Item not found: {remote_drivewsid}",
            ) from exc

    def _ensure_parent_path(self, path: str) -> BackendItem:
        normalized = self._normalize_path(path)
        for item in self._items.values():
            if item.path == normalized and item.item_type == BackendItemType.FOLDER:
                return item
        parent = self._ensure_parent_path(posixpath.dirname(normalized) or "/")
        return self._create_item(
            parent.remote_drivewsid,
            posixpath.basename(normalized),
            BackendItemType.FOLDER,
            b"",
        )

    def _create_item(
        self,
        parent_drivewsid: str,
        name: str,
        item_type: BackendItemType,
        content: bytes,
        *,
        remote_shareid: Mapping[str, Any] | str | None = None,
    ) -> BackendItem:
        parent = self._require_item(parent_drivewsid)
        if parent.item_type != BackendItemType.FOLDER:
            raise BackendError(
                BackendErrorCode.CONTRACT_MISMATCH,
                f"{parent_drivewsid} is not a folder",
            )
        item_id = self._new_id(item_type.value)
        path = self._join_path(parent.path, name)
        item = BackendItem(
            path=path,
            name=name,
            item_type=item_type,
            remote_drivewsid=item_id,
            parent_drivewsid=parent.remote_drivewsid,
            parent_path=parent.path,
            remote_docwsid=f"doc-{item_id}" if item_type == BackendItemType.FILE else None,
            remote_etag=self._new_etag(item_id),
            remote_zone="fake-zone",
            remote_shareid=remote_shareid,
            size=len(content) if item_type == BackendItemType.FILE else 0,
            mtime=self._now(),
            metadata={"source": "fake"},
        )
        self._items[item.remote_drivewsid] = item
        if item.item_type == BackendItemType.FILE:
            self._content[item.remote_drivewsid] = content
        return item

    def _relocate_subtree(
        self,
        item: BackendItem,
        new_path: str,
        new_name: str,
        new_parent_drivewsid: str | None,
    ) -> BackendItem:
        old_prefix = item.path.rstrip("/") + "/"
        relocated: dict[str, BackendItem] = {}
        new_parent = self._require_item(new_parent_drivewsid or "root")
        for current in list(self._items.values()):
            if current.remote_drivewsid == item.remote_drivewsid:
                relocated[current.remote_drivewsid] = replace(
                    current,
                    path=new_path,
                    name=new_name,
                    parent_drivewsid=new_parent.remote_drivewsid,
                    parent_path=new_parent.path,
                    remote_etag=self._new_etag(current.remote_drivewsid),
                    mtime=self._now(),
                )
                continue
            if current.path.startswith(old_prefix):
                suffix = current.path[len(old_prefix) :]
                parent_path = posixpath.dirname(self._join_path(new_path, suffix)) or "/"
                relocated[current.remote_drivewsid] = replace(
                    current,
                    path=self._join_path(new_path, suffix),
                    parent_path=parent_path,
                    mtime=self._now(),
                )
        self._items.update(relocated)
        return self._items[item.remote_drivewsid]

    def _new_id(self, prefix: str) -> str:
        self._counter += 1
        return f"{prefix}-{self._counter}"

    def _new_etag(self, item_id: str) -> str:
        return f"etag-{item_id}-{self._counter}"

    def _now(self) -> int:
        return int(time.time())

    def _normalize_path(self, path: str) -> str:
        normalized = posixpath.normpath("/" + path.strip("/"))
        return "/" if normalized == "/." else normalized

    def _join_path(self, parent_path: str, name: str) -> str:
        return "/" + name if parent_path == "/" else parent_path.rstrip("/") + "/" + name

