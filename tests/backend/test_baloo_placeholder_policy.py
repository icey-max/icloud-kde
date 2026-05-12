"""Baloo-safe placeholder read policy tests for the vendored driver."""

from __future__ import annotations

import os
import shutil
import tempfile
import unittest
from unittest.mock import Mock

from tests.helpers.load_vendor_driver import load_vendor_driver


class BalooPlaceholderPolicyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.driver = load_vendor_driver()
        self.root = tempfile.mkdtemp(prefix="icloud-kde-baloo-policy-")
        self.mirror = self.driver.LocalMirror(self.root)
        self.state = self.driver.SyncState(os.path.join(self.root, "state.sqlite3"))
        api = Mock()
        api.drive.root = Mock()
        self.engine = self.driver.ICloudSyncEngine(api, self.mirror, self.state, Mock())

    def tearDown(self) -> None:
        self.engine.shutdown()
        shutil.rmtree(self.root)

    def _filesystem(self, process_name: str | None = None):
        filesystem = self.driver.ICloudFS()
        filesystem.mirror = self.mirror
        filesystem.state = self.state
        filesystem.sync_engine = self.engine
        filesystem.logger = Mock()
        filesystem._fuse_process_name_for_tests = process_name
        return filesystem

    def _remote_placeholder(self, path: str = "/docs/a.txt", *, dirty: bool = False) -> None:
        self.state.upsert_entry(
            {
                "path": path,
                "type": "file",
                "parent_path": "/docs",
                "remote_drivewsid": f"file-{path}",
                "remote_docwsid": f"doc-{path}",
                "remote_etag": "etag-1",
                "remote_zone": "zone-1",
                "size": 12,
                "mtime": 123,
                "hydrated": False,
                "dirty": dirty,
                "tombstone": False,
                "synced_path": path,
            }
        )

    def test_normal_open_hydrates_clean_unhydrated_file(self) -> None:
        self._remote_placeholder()
        filesystem = self._filesystem()
        self.engine.ensure_local_file = Mock()

        result = filesystem.open("/docs/a.txt", os.O_RDONLY)

        self.assertEqual(result, 0)
        self.engine.ensure_local_file.assert_called_once_with("/docs/a.txt")

    def test_baloo_open_does_not_hydrate_clean_remote_placeholder(self) -> None:
        self._remote_placeholder()
        filesystem = self._filesystem("baloo_file_extractor")
        self.engine.ensure_local_file = Mock()

        result = filesystem.open("/docs/a.txt", os.O_RDONLY)

        self.assertEqual(result, 0)
        self.engine.ensure_local_file.assert_not_called()
        self.assertEqual(self.state.get_entry("/docs/a.txt")["hydrated"], 0)

    def test_kfilemetadata_read_returns_empty_bytes_without_hydrating(self) -> None:
        self._remote_placeholder()
        filesystem = self._filesystem("kfilemetadata")
        self.engine.ensure_local_file = Mock()

        result = filesystem.read("/docs/a.txt", 4096, 0)

        self.assertEqual(result, b"")
        self.engine.ensure_local_file.assert_not_called()
        self.assertEqual(self.state.get_entry("/docs/a.txt")["hydrated"], 0)

    def test_dirty_unhydrated_files_are_not_treated_as_remote_only_placeholders(self) -> None:
        self._remote_placeholder("/docs/dirty.txt", dirty=True)
        self.mirror.write_atomic_bytes("/docs/dirty.txt", b"dirty local content", 123)
        filesystem = self._filesystem("baloo_file_extractor")
        self.engine.ensure_local_file = Mock()

        result = filesystem.read("/docs/dirty.txt", 4096, 0)

        self.assertEqual(result, b"dirty local content")
        self.engine.ensure_local_file.assert_not_called()


if __name__ == "__main__":
    unittest.main()
