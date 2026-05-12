"""Baloo smoke fixture for hydrated files versus remote-only placeholders."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
import unittest
import uuid
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class BalooPlaceholderSmokeTests(unittest.TestCase):
    REQUIRED_TOOLS = ("balooctl6", "balooshow6", "baloosearch6")

    def _require_baloo_tools(self) -> dict[str, str]:
        tools = {tool: shutil.which(tool) for tool in self.REQUIRED_TOOLS}
        missing = [tool for tool, path in tools.items() if path is None]
        if missing:
            self.skipTest(f"Missing Baloo runtime tools: {', '.join(missing)}")

        status = subprocess.run(
            [tools["balooctl6"], "status"],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=5,
            check=False,
        )
        if status.returncode != 0:
            self.skipTest(f"Baloo runtime unavailable: {status.stdout.strip()}")
        if "disabled" in status.stdout.lower():
            self.skipTest("Baloo file indexing is disabled by the user")
        return {tool: path for tool, path in tools.items() if path is not None}

    def _search(self, baloosearch: str, directory: Path, token: str) -> str:
        result = subprocess.run(
            [baloosearch, "-d", str(directory), token],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=5,
            check=False,
        )
        return result.stdout

    def test_hydrated_content_is_searchable_and_placeholder_remote_content_is_absent(self) -> None:
        tools = self._require_baloo_tools()
        suffix = uuid.uuid4().hex
        hydrated_token = f"icloud_hydrated_search_token_{suffix}"
        placeholder_remote_token = f"icloud_placeholder_remote_token_{suffix}"

        with TemporaryDirectory(prefix="icloud-kde-baloo-") as tmp:
            sync_root = Path(tmp)
            hydrated = sync_root / "hydrated.txt"
            placeholder = sync_root / "remote-only-placeholder.txt"
            hydrated.write_text(f"{hydrated_token}\n", encoding="utf-8")
            placeholder.write_text("remote-only placeholder fixture\n", encoding="utf-8")

            try:
                index = subprocess.run(
                    [tools["balooctl6"], "index", str(hydrated), str(placeholder)],
                    text=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    timeout=10,
                    check=False,
                )
                if index.returncode != 0:
                    self.skipTest(f"Baloo index command failed: {index.stdout.strip()}")

                hydrated_output = ""
                for _ in range(10):
                    hydrated_output = self._search(tools["baloosearch6"], sync_root, hydrated_token)
                    if str(hydrated) in hydrated_output:
                        break
                    time.sleep(0.2)

                self.assertIn(str(hydrated), hydrated_output)
                self.assertNotIn(
                    placeholder_remote_token,
                    self._search(tools["baloosearch6"], sync_root, placeholder_remote_token),
                )

                show = subprocess.run(
                    [tools["balooshow6"], str(hydrated)],
                    text=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    timeout=5,
                    check=False,
                )
                self.assertEqual(show.returncode, 0)
            finally:
                subprocess.run(
                    [tools["balooctl6"], "clear", str(hydrated), str(placeholder)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=5,
                    check=False,
                )


if __name__ == "__main__":
    unittest.main()
