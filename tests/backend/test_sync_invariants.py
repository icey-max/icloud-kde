"""Sync safety invariants for the vendored icloud-linux engine."""

from __future__ import annotations

import errno
import os
import shutil
import stat
import tempfile
import unittest
from unittest.mock import Mock

from tests.helpers.load_vendor_driver import load_vendor_driver


class SyncInvariantTests(unittest.TestCase):
    def setUp(self) -> None:
        self.driver = load_vendor_driver()
        self.root = tempfile.mkdtemp(prefix="icloud-kde-sync-invariants-")
        self.mirror = self.driver.LocalMirror(self.root)
        self.state = self.driver.SyncState(os.path.join(self.root, "state.sqlite3"))
        api = Mock()
        api.drive.root = Mock()
        self.engine = self.driver.ICloudSyncEngine(api, self.mirror, self.state, Mock())

    def tearDown(self) -> None:
        self.engine.shutdown()
        shutil.rmtree(self.root)

    def _filesystem(self):
        filesystem = self.driver.ICloudFS()
        filesystem.mirror = self.mirror
        filesystem.state = self.state
        filesystem.sync_engine = self.engine
        filesystem.logger = Mock()
        return filesystem

    def test_mknod_rejects_non_regular_special_files(self) -> None:
        filesystem = self._filesystem()

        result = filesystem.mknod("/fifo", stat.S_IFIFO, 0)

        self.assertEqual(result, -errno.ENOSYS)
        self.assertFalse(self.mirror.exists("/fifo"))

    def test_conflict_copy_clears_remote_identity_and_stays_dirty(self) -> None:
        self.state.upsert_entry(
            {
                "path": "/docs",
                "type": "folder",
                "parent_path": "/",
                "remote_drivewsid": "folder-1",
                "remote_shareid": {"share-zone": "folder"},
                "hydrated": True,
                "dirty": True,
                "tombstone": False,
                "synced_path": "/docs",
            }
        )
        self.state.upsert_entry(
            {
                "path": "/docs/a.txt",
                "type": "file",
                "parent_path": "/docs",
                "remote_drivewsid": "file-1",
                "remote_docwsid": "doc-1",
                "remote_etag": "etag-1",
                "remote_zone": "zone-1",
                "remote_shareid": {"share-zone": "file"},
                "hydrated": True,
                "dirty": True,
                "tombstone": False,
                "synced_path": "/docs/a.txt",
            }
        )

        self.state.detach_subtree_as_conflict("/docs", "/docs.local-conflict-123")

        folder = self.state.get_entry("/docs.local-conflict-123")
        child = self.state.get_entry("/docs.local-conflict-123/a.txt")
        self.assertIsNone(folder["remote_drivewsid"])
        self.assertIsNone(folder["remote_shareid"])
        self.assertIsNone(child["remote_docwsid"])
        self.assertIsNone(child["remote_etag"])
        self.assertIsNone(child["remote_zone"])
        self.assertIsNone(child["synced_path"])
        self.assertEqual(folder["dirty"], 1)
        self.assertEqual(child["dirty"], 1)
        self.assertEqual(child["tombstone"], 0)

    def test_remote_delete_of_dirty_content_preserves_local_upload_candidate(self) -> None:
        self.mirror.ensure_dir("/docs")
        self.mirror.write_atomic_bytes("/docs/a.txt", b"local edit", 123)
        self.state.upsert_entry(
            {
                "path": "/docs/a.txt",
                "type": "file",
                "parent_path": "/docs",
                "remote_drivewsid": "file-1",
                "remote_docwsid": "doc-1",
                "remote_etag": "etag-1",
                "remote_zone": "zone-1",
                "remote_shareid": {"share-zone": "file"},
                "size": 10,
                "mtime": 123,
                "hydrated": True,
                "dirty": True,
                "tombstone": False,
                "synced_path": "/docs/a.txt",
            }
        )

        self.engine._apply_remote_snapshot({})

        entry = self.state.get_entry("/docs/a.txt")
        self.assertIsNotNone(entry)
        self.assertTrue(self.mirror.exists("/docs/a.txt"))
        self.assertIsNone(entry["remote_drivewsid"])
        self.assertIsNone(entry["remote_docwsid"])
        self.assertIsNone(entry["remote_etag"])
        self.assertIsNone(entry["remote_zone"])
        self.assertIsNone(entry["remote_shareid"])
        self.assertEqual(entry["dirty"], 1)
        self.assertEqual(entry["tombstone"], 0)

    def test_open_hydrates_unhydrated_clean_file(self) -> None:
        self.state.upsert_entry(
            {
                "path": "/docs/a.txt",
                "type": "file",
                "parent_path": "/docs",
                "remote_drivewsid": "file-1",
                "remote_docwsid": "doc-1",
                "remote_etag": "etag-1",
                "remote_zone": "zone-1",
                "size": 4,
                "mtime": 123,
                "hydrated": False,
                "dirty": False,
                "tombstone": False,
                "synced_path": "/docs/a.txt",
            }
        )
        filesystem = self._filesystem()
        self.engine.ensure_local_file = Mock()

        result = filesystem.open("/docs/a.txt", os.O_RDONLY)

        self.assertEqual(result, 0)
        self.engine.ensure_local_file.assert_called_once_with("/docs/a.txt")

    def test_local_rename_preserves_synced_path_and_marks_dirty(self) -> None:
        self.mirror.ensure_dir("/docs")
        self.mirror.write_atomic_bytes("/docs/a.txt", b"content", 123)
        self.state.upsert_entry(
            {
                "path": "/docs/a.txt",
                "type": "file",
                "parent_path": "/docs",
                "remote_drivewsid": "file-1",
                "remote_docwsid": "doc-1",
                "remote_etag": "etag-1",
                "remote_zone": "zone-1",
                "size": 7,
                "mtime": 123,
                "hydrated": True,
                "dirty": False,
                "tombstone": False,
                "synced_path": "/docs/a.txt",
            }
        )
        filesystem = self._filesystem()

        result = filesystem.rename("/docs/a.txt", "/docs/b.txt")

        renamed = self.state.get_entry("/docs/b.txt")
        self.assertEqual(result, 0)
        self.assertIsNotNone(renamed)
        self.assertEqual(renamed["dirty"], 1)
        self.assertEqual(renamed["synced_path"], "/docs/a.txt")
        self.assertTrue(self.mirror.exists("/docs/b.txt"))
        self.assertFalse(self.mirror.exists("/docs/a.txt"))

    def test_start_uses_persistent_cache_without_initial_scan(self) -> None:
        self.state.upsert_entry(
            {
                "path": "/docs",
                "type": "folder",
                "parent_path": "/",
                "hydrated": True,
                "dirty": False,
                "tombstone": False,
                "synced_path": "/docs",
            }
        )
        engine = self.driver.ICloudSyncEngine(
            Mock(),
            self.mirror,
            self.state,
            Mock(),
        )
        engine.initial_scan = Mock()
        engine._reconcile_persistent_cache = Mock()
        engine._schedule_all_unhydrated = Mock()
        engine._start_background_threads = Mock()

        try:
            engine.start()

            engine.initial_scan.assert_not_called()
            engine._reconcile_persistent_cache.assert_called_once()
            engine._schedule_all_unhydrated.assert_called_once()
            engine._start_background_threads.assert_called_once()
        finally:
            engine.shutdown()

    def test_retry_backoff_is_exponential_and_capped(self) -> None:
        self.assertEqual(self.engine._retry_delay_for_attempt(1), 5)
        self.assertEqual(self.engine._retry_delay_for_attempt(2), 10)
        self.assertEqual(self.engine._retry_delay_for_attempt(3), 20)
        self.assertEqual(self.engine._retry_delay_for_attempt(7), 300)
        self.assertEqual(self.engine._retry_delay_for_attempt(12), 300)

    def test_download_concurrency_is_conservative(self) -> None:
        engine = self.driver.ICloudSyncEngine(
            Mock(),
            self.mirror,
            self.state,
            Mock(),
            warmup_workers=5,
        )
        try:
            self.assertEqual(engine.warmup_workers, 5)
            self.assertEqual(engine.download_semaphore._value, 1)
        finally:
            engine.shutdown()

    def test_shared_metadata_round_trips_through_state(self) -> None:
        self.state.upsert_entry(
            {
                "path": "/shared/a.txt",
                "type": "file",
                "parent_path": "/shared",
                "remote_drivewsid": "file-1",
                "remote_docwsid": "doc-1",
                "remote_etag": "etag-1",
                "remote_zone": "zone-1",
                "remote_shareid": {"share-zone": "abc"},
                "hydrated": False,
                "dirty": False,
                "tombstone": False,
                "synced_path": "/shared/a.txt",
            }
        )

        entry = self.state.get_entry("/shared/a.txt")

        self.assertEqual(entry["remote_shareid"], {"share-zone": "abc"})
        self.assertEqual(entry["remote_docwsid"], "doc-1")
        self.assertEqual(entry["remote_etag"], "etag-1")
        self.assertEqual(entry["remote_zone"], "zone-1")


if __name__ == "__main__":
    unittest.main()
