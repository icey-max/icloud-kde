"""Tests for daemon filesystem semantics classification."""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from icloud_kde.daemon.filesystem import (  # noqa: E402
    classify_path,
    is_supported_path,
    scan_unsupported_entries,
)


class FilesystemSemanticsTests(unittest.TestCase):
    def test_regular_file_and_directory_are_supported(self) -> None:
        with TemporaryDirectory() as tmp:
            base = Path(tmp)
            folder = base / "docs"
            file_path = folder / "a.txt"
            folder.mkdir()
            file_path.write_text("content", encoding="utf-8")

            folder_semantics = classify_path(folder)
            file_semantics = classify_path(file_path)

            self.assertTrue(is_supported_path(folder))
            self.assertTrue(is_supported_path(file_path))
            self.assertEqual(folder_semantics.file_type, "directory")
            self.assertEqual(file_semantics.file_type, "regular_file")

    def test_symlink_is_reported_unsupported_without_following_target(self) -> None:
        with TemporaryDirectory() as tmp:
            base = Path(tmp)
            target = base / "target.txt"
            link = base / "link.txt"
            target.write_text("target", encoding="utf-8")
            link.symlink_to(target)

            semantics = classify_path(link)

            self.assertFalse(semantics.supported)
            self.assertEqual(semantics.file_type, "symlink")
            self.assertIn("Symlinks", semantics.reason)

    def test_fifo_is_reported_unsupported(self) -> None:
        if not hasattr(os, "mkfifo"):
            self.skipTest("mkfifo is not available on this platform")
        with TemporaryDirectory() as tmp:
            fifo = Path(tmp) / "queue"
            os.mkfifo(fifo)

            semantics = classify_path(fifo)

            self.assertFalse(semantics.supported)
            self.assertEqual(semantics.file_type, "fifo")
            self.assertIn("FIFOs", semantics.reason)

    def test_scan_unsupported_entries_returns_posix_paths(self) -> None:
        with TemporaryDirectory() as tmp:
            base = Path(tmp)
            nested = base / "nested"
            nested.mkdir()
            (nested / "link").symlink_to(base / "missing-target")

            entries = scan_unsupported_entries(base)

            self.assertEqual(len(entries), 1)
            self.assertEqual(entries[0].path, "/nested/link")
            self.assertEqual(entries[0].file_type, "symlink")


if __name__ == "__main__":
    unittest.main()
