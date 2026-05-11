"""Tests for public daemon state mapping."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from icloud_kde.daemon.state import (  # noqa: E402
    ItemState,
    ServiceState,
    item_state_from_entry,
)


class DaemonStateTests(unittest.TestCase):
    def _entry(self, **overrides):
        entry = {
            "path": "/docs/a.txt",
            "type": "file",
            "hydrated": True,
            "dirty": False,
            "tombstone": False,
            "size": 1,
            "mtime": 1,
        }
        entry.update(overrides)
        return entry

    def test_clean_hydrated_file_maps_to_hydrated(self) -> None:
        self.assertEqual(item_state_from_entry(self._entry()), ItemState.HYDRATED)

    def test_clean_unhydrated_file_maps_to_placeholder(self) -> None:
        state = item_state_from_entry(self._entry(hydrated=False))

        self.assertEqual(state, ItemState.PLACEHOLDER)

    def test_dirty_file_maps_to_dirty(self) -> None:
        state = item_state_from_entry(self._entry(dirty=True, hydrated=False))

        self.assertEqual(state, ItemState.DIRTY)

    def test_auth_required_stays_distinct(self) -> None:
        state = item_state_from_entry(
            self._entry(hydrated=True),
            service_state=ServiceState.AUTH_REQUIRED,
        )

        self.assertEqual(state, ItemState.AUTH_REQUIRED)

    def test_conflict_and_unsupported_override_generic_state(self) -> None:
        entry = self._entry(hydrated=True)

        conflicted = item_state_from_entry(
            entry,
            service_state=ServiceState.OFFLINE,
            conflict_paths={"/docs/a.txt"},
        )
        unsupported = item_state_from_entry(
            entry,
            service_state=ServiceState.AUTH_REQUIRED,
            unsupported_paths={"/docs/a.txt"},
        )

        self.assertEqual(conflicted, ItemState.CONFLICTED)
        self.assertEqual(unsupported, ItemState.UNSUPPORTED)


if __name__ == "__main__":
    unittest.main()
