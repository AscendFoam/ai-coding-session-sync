from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tests.cli_test_utils import run_cli


class CliSmokeTest(unittest.TestCase):
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
            self.assertTrue(latest_data["snapshot_id"])

            imported = run_cli(tmp_path, "import", "--tool", "codex", "--print-prompt")
            self.assertEqual(imported.returncode, 0, imported.stderr)
            self.assertIn("Ship the MVP handoff flow", imported.stdout)
            self.assertIn("不要假设可以原生恢复同一个 session", imported.stdout)

    def test_latest_show_and_resolve_conflict_pointer(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            init = run_cli(tmp_path, "init")
            self.assertEqual(init.returncode, 0, init.stderr)

            latest_dir = tmp_path / ".ai-session-sync" / "latest"
            manifests_dir = tmp_path / ".ai-session-sync" / "manifests"
            manifests_dir.mkdir(exist_ok=True)
            (manifests_dir / "20260425T080000Z-sample-macbook-codex.json").write_text("{}\n", encoding="utf-8")
            (manifests_dir / "20260425T080300Z-sample-windows-codex.json").write_text("{}\n", encoding="utf-8")
            (latest_dir / "codex.json").write_text(
                json.dumps(
                    {
                        "candidates": [
                            "20260425T080300Z-sample-windows-codex",
                            "20260425T080000Z-sample-macbook-codex",
                        ],
                        "requires_selection": True,
                    },
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

            show = run_cli(tmp_path, "latest", "show", "--tool", "codex")
            self.assertEqual(show.returncode, 0, show.stderr)
            self.assertIn("Latest pointer requires selection.", show.stdout)

            resolve = run_cli(
                tmp_path,
                "latest",
                "resolve",
                "--tool",
                "codex",
                "20260425T080300Z-sample-windows-codex",
            )
            self.assertEqual(resolve.returncode, 0, resolve.stderr)

            latest_data = json.loads((latest_dir / "codex.json").read_text(encoding="utf-8"))
            self.assertEqual(latest_data["snapshot_id"], "20260425T080300Z-sample-windows-codex")
            self.assertEqual(
                latest_data["manifest"],
                "manifests/20260425T080300Z-sample-windows-codex.json",
            )

    def test_status_and_doctor_surface_sidecar_config_problems(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            init = run_cli(
                tmp_path,
                "init",
                "--backend",
                "git",
                "--storage",
                "sidecar-repo",
            )
            self.assertEqual(init.returncode, 0, init.stderr)

            status = run_cli(tmp_path, "status", "--tool", "codex")
            self.assertEqual(status.returncode, 0, status.stderr)
            self.assertIn("Storage: sidecar-repo", status.stdout)
            self.assertIn("Latest state: missing", status.stdout)
            self.assertIn("sidecar git remote is not configured", status.stdout)

            doctor = run_cli(tmp_path, "doctor", "--tool", "codex")
            self.assertEqual(doctor.returncode, 0, doctor.stderr)
            self.assertIn("Backend: git", doctor.stdout)
            self.assertIn("Latest state: missing", doctor.stdout)
            self.assertIn("warning: sidecar git remote is not configured", doctor.stdout)
            self.assertIn("Run `aiss export --tool codex|claude` or `aiss pull` to create sync state.", doctor.stdout)


if __name__ == "__main__":
    unittest.main()
