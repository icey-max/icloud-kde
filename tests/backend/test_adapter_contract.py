"""Contract tests for the project-owned iCloud Drive backend adapter."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from icloud_kde.backend.contract import (  # noqa: E402
    BackendError,
    BackendErrorCode,
    BackendItemType,
    RetryHint,
)
from tests.fakes.fake_icloud_backend import FakeICloudDriveBackend  # noqa: E402


class AdapterContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.backend = FakeICloudDriveBackend()

    def test_validate_session_and_capabilities(self) -> None:
        session = self.backend.validate_session()
        capabilities = self.backend.get_capabilities()

        self.assertTrue(session.authenticated)
        self.assertTrue(capabilities.supports_upload)
        self.assertTrue(capabilities.supports_rename)
        self.assertTrue(capabilities.supports_move)
        self.assertTrue(capabilities.supports_delete)
        self.assertTrue(capabilities.supports_shared_metadata)
        self.assertEqual(capabilities.max_parallel_downloads, 1)

    def test_list_tree_returns_metadata(self) -> None:
        self.backend.seed_folder("/docs")
        file_item = self.backend.seed_file(
            "/docs/a.txt",
            b"hello",
            remote_shareid={"share-zone": "abc"},
        )

        items = self.backend.list_tree()
        paths = {item.path for item in items}

        self.assertIn("/docs", paths)
        self.assertIn("/docs/a.txt", paths)
        self.assertEqual(file_item.item_type, BackendItemType.FILE)
        self.assertEqual(file_item.remote_docwsid, f"doc-{file_item.remote_drivewsid}")
        self.assertEqual(file_item.remote_zone, "fake-zone")
        self.assertEqual(file_item.remote_shareid, {"share-zone": "abc"})

    def test_metadata_lookup_and_download(self) -> None:
        file_item = self.backend.seed_file("/notes/todo.txt", b"todo")

        metadata = self.backend.get_item_metadata(file_item.remote_drivewsid)
        content = self.backend.download_file(metadata)

        self.assertEqual(metadata.path, "/notes/todo.txt")
        self.assertEqual(metadata.size, 4)
        self.assertEqual(content, b"todo")

    def test_upload_rename_move_delete_cycle(self) -> None:
        docs = self.backend.create_folder("root", "docs")
        upload = self.backend.upload_file(docs.remote_drivewsid, "draft.txt", b"v1")

        replaced = self.backend.upload_file(
            docs.remote_drivewsid,
            "draft.txt",
            b"v2",
            replace_drivewsid=upload.item.remote_drivewsid,
        )
        renamed = self.backend.rename_item(replaced.item.remote_drivewsid, "final.txt")
        archive = self.backend.create_folder("root", "archive")
        moved = self.backend.move_item(renamed.remote_drivewsid, archive.remote_drivewsid)

        self.assertTrue(upload.created)
        self.assertTrue(replaced.replaced)
        self.assertEqual(self.backend.download_file(moved), b"v2")
        self.assertEqual(moved.path, "/archive/final.txt")

        self.backend.delete_item(moved.remote_drivewsid)
        with self.assertRaises(BackendError) as raised:
            self.backend.get_item_metadata(moved.remote_drivewsid)
        self.assertEqual(raised.exception.code, BackendErrorCode.NOT_FOUND)

    def test_shared_metadata_round_trip(self) -> None:
        file_item = self.backend.seed_file(
            "/shared/report.txt",
            b"report",
            remote_shareid={"share-zone": "shared-1"},
        )

        shared = self.backend.get_shared_metadata(
            file_item.remote_drivewsid,
            {"share-zone": "shared-1"},
        )

        self.assertEqual(shared["remote_drivewsid"], file_item.remote_drivewsid)
        self.assertEqual(shared["remote_shareid"], {"share-zone": "shared-1"})
        self.assertEqual(shared["path"], "/shared/report.txt")

    def test_injected_error_is_normalized(self) -> None:
        self.backend.inject_error(
            "list_tree",
            BackendError(
                BackendErrorCode.THROTTLED,
                "slow down",
                RetryHint(retryable=True, delay_seconds=30, reason="test"),
            ),
        )

        with self.assertRaises(BackendError) as raised:
            self.backend.list_tree()

        self.assertEqual(raised.exception.code, BackendErrorCode.THROTTLED)
        self.assertTrue(raised.exception.retry_hint.retryable)
        self.assertEqual(raised.exception.retry_hint.delay_seconds, 30)


if __name__ == "__main__":
    unittest.main()

