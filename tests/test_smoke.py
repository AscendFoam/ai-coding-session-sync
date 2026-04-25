from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tests.schema_utils import assert_matches_schema, load_schema


def run_cli(tmp_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1] / "src")
    return subprocess.run(
        [sys.executable, "-m", "aiss", *args],
        cwd=tmp_path,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        env=env,
    )


class CliSmokeTest(unittest.TestCase):
    def setUp(self) -> None:
        self.latest_pointer_schema = load_schema("latest-pointer.schema.json")
        self.manifest_schema = load_schema("manifest.schema.json")

    def test_init_export_import_prompt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            init = run_cli(tmp_path, "init")
            self.assertEqual(init.returncode, 0, init.stderr)
            self.assertTrue((tmp_path / ".ai-session-sync" / "config.toml").exists())

            export = run_cli(tmp_path, "export", "--tool", "codex", "--goal", "Ship the MVP handoff flow")
            self.assertEqual(export.returncode, 0, export.stderr)
            latest = tmp_path / ".ai-session-sync" / "latest" / "codex.json"
            latest_data = json.loads(latest.read_text(encoding="utf-8"))
            assert_matches_schema(latest_data, self.latest_pointer_schema)
            self.assertTrue(latest_data["snapshot_id"])
            manifest_path = tmp_path / ".ai-session-sync" / latest_data["manifest"]
            manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
            assert_matches_schema(manifest_data, self.manifest_schema)

            imported = run_cli(tmp_path, "import", "--tool", "codex", "--print-prompt")
            self.assertEqual(imported.returncode, 0, imported.stderr)
            self.assertIn("Ship the MVP handoff flow", imported.stdout)
            self.assertIn("不要假设可以原生恢复同一个 session", imported.stdout)


if __name__ == "__main__":
    unittest.main()
