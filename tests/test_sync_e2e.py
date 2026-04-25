from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tests.cli_test_utils import run_cli, run_command


class SyncE2ETest(unittest.TestCase):
    def test_push_pull_round_trip_between_two_devices(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            remote = tmp_path / "sync-state.git"
            mac_project = tmp_path / "mac" / "sample-project"
            windows_project = tmp_path / "windows" / "sample-project"

            self._init_bare_remote(remote)
            self._init_project(mac_project, remote, device_id="sample-macbook")
            self._init_project(windows_project, remote, device_id="sample-windows")

            export = run_cli(
                mac_project,
                "export",
                "--tool",
                "codex",
                "--goal",
                "Ship the sidecar sync MVP",
                extra_env={
                    "AISS_DEVICE_ID": "sample-macbook",
                    "AISS_FIXED_NOW": "2026-04-25T08:00:00Z",
                },
            )
            self.assertEqual(export.returncode, 0, export.stderr)

            push = run_cli(mac_project, "push", extra_env={"AISS_DEVICE_ID": "sample-macbook"})
            self.assertEqual(push.returncode, 0, push.stderr)
            self.assertIn("Pushed sidecar commit:", push.stdout)

            pull = run_cli(windows_project, "pull", extra_env={"AISS_DEVICE_ID": "sample-windows"})
            self.assertEqual(pull.returncode, 0, pull.stderr)
            self.assertIn("Copied files:", pull.stdout)

            latest = json.loads((windows_project / ".ai-session-sync" / "latest" / "codex.json").read_text(encoding="utf-8"))
            manifest = json.loads((windows_project / ".ai-session-sync" / latest["manifest"]).read_text(encoding="utf-8"))
            self.assertEqual(latest["snapshot_id"], "20260425T080000Z-sample-macbook-codex")
            self.assertEqual(manifest["snapshot_id"], latest["snapshot_id"])

            imported = run_cli(windows_project, "import", "--tool", "codex", "--print-prompt")
            self.assertEqual(imported.returncode, 0, imported.stderr)
            self.assertIn("Ship the sidecar sync MVP", imported.stdout)
            self.assertIn("不要假设可以原生恢复同一个 session", imported.stdout)

        return None

    def test_sync_pulls_exports_and_pushes_newer_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            remote = tmp_path / "sync-state.git"
            mac_project = tmp_path / "mac" / "sample-project"
            windows_project = tmp_path / "windows" / "sample-project"

            self._init_bare_remote(remote)
            self._init_project(mac_project, remote, device_id="sample-macbook")
            self._init_project(windows_project, remote, device_id="sample-windows")

            first_export = run_cli(
                mac_project,
                "export",
                "--tool",
                "codex",
                "--goal",
                "Export the first sidecar snapshot",
                extra_env={
                    "AISS_DEVICE_ID": "sample-macbook",
                    "AISS_FIXED_NOW": "2026-04-25T08:00:00Z",
                },
            )
            self.assertEqual(first_export.returncode, 0, first_export.stderr)
            first_push = run_cli(mac_project, "push", extra_env={"AISS_DEVICE_ID": "sample-macbook"})
            self.assertEqual(first_push.returncode, 0, first_push.stderr)

            sync = run_cli(
                windows_project,
                "sync",
                "--tool",
                "codex",
                "--goal",
                "Continue from the Windows machine",
                extra_env={
                    "AISS_DEVICE_ID": "sample-windows",
                    "AISS_FIXED_NOW": "2026-04-25T08:05:00Z",
                },
            )
            self.assertEqual(sync.returncode, 0, sync.stderr)
            self.assertIn("Pulling sidecar state...", sync.stdout)
            self.assertIn("Exporting new snapshot...", sync.stdout)
            self.assertIn("Pushing sidecar state...", sync.stdout)

            pull_back = run_cli(mac_project, "pull", extra_env={"AISS_DEVICE_ID": "sample-macbook"})
            self.assertEqual(pull_back.returncode, 0, pull_back.stderr)

            latest = json.loads((mac_project / ".ai-session-sync" / "latest" / "codex.json").read_text(encoding="utf-8"))
            self.assertEqual(latest["snapshot_id"], "20260425T080500Z-sample-windows-codex")

            imported = run_cli(mac_project, "import", "--tool", "codex", "--print-prompt")
            self.assertEqual(imported.returncode, 0, imported.stderr)
            self.assertIn("Continue from the Windows machine", imported.stdout)

        return None

    def test_latest_conflict_is_generated_and_can_be_resolved(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            remote = tmp_path / "sync-state.git"
            mac_project = tmp_path / "mac" / "sample-project"
            windows_project = tmp_path / "windows" / "sample-project"

            self._init_bare_remote(remote)
            self._init_project(mac_project, remote, device_id="sample-macbook")
            self._init_project(windows_project, remote, device_id="sample-windows")

            mac_export = run_cli(
                mac_project,
                "export",
                "--tool",
                "codex",
                "--goal",
                "Mac exported before the pull",
                extra_env={
                    "AISS_DEVICE_ID": "sample-macbook",
                    "AISS_FIXED_NOW": "2026-04-25T08:00:00Z",
                },
            )
            self.assertEqual(mac_export.returncode, 0, mac_export.stderr)
            mac_push = run_cli(mac_project, "push", extra_env={"AISS_DEVICE_ID": "sample-macbook"})
            self.assertEqual(mac_push.returncode, 0, mac_push.stderr)

            windows_export = run_cli(
                windows_project,
                "export",
                "--tool",
                "codex",
                "--goal",
                "Windows exported offline before pulling",
                extra_env={
                    "AISS_DEVICE_ID": "sample-windows",
                    "AISS_FIXED_NOW": "2026-04-25T08:03:00Z",
                },
            )
            self.assertEqual(windows_export.returncode, 0, windows_export.stderr)

            windows_push = run_cli(windows_project, "push", extra_env={"AISS_DEVICE_ID": "sample-windows"})
            self.assertEqual(windows_push.returncode, 0, windows_push.stderr)

            mac_pull = run_cli(mac_project, "pull", extra_env={"AISS_DEVICE_ID": "sample-macbook"})
            self.assertEqual(mac_pull.returncode, 0, mac_pull.stderr)

            latest = json.loads((mac_project / ".ai-session-sync" / "latest" / "codex.json").read_text(encoding="utf-8"))
            self.assertTrue(latest["requires_selection"])
            self.assertEqual(
                latest["candidates"],
                [
                    "20260425T080300Z-sample-windows-codex",
                    "20260425T080000Z-sample-macbook-codex",
                ],
            )

            latest_show = run_cli(mac_project, "latest", "show", "--tool", "codex")
            self.assertEqual(latest_show.returncode, 0, latest_show.stderr)
            self.assertIn("Latest pointer requires selection.", latest_show.stdout)
            self.assertIn("20260425T080300Z-sample-windows-codex", latest_show.stdout)

            latest_import = run_cli(mac_project, "import", "--tool", "codex", "--print-prompt")
            self.assertNotEqual(latest_import.returncode, 0)
            combined = f"{latest_import.stdout}\n{latest_import.stderr}"
            self.assertIn("Latest snapshot requires selection.", combined)
            self.assertIn("aiss latest resolve --tool codex <snapshot_id>", combined)

            resolve = run_cli(
                mac_project,
                "latest",
                "resolve",
                "--tool",
                "codex",
                "20260425T080300Z-sample-windows-codex",
            )
            self.assertEqual(resolve.returncode, 0, resolve.stderr)
            self.assertIn("Resolved latest pointer for codex", resolve.stdout)

            resolved_latest = json.loads((mac_project / ".ai-session-sync" / "latest" / "codex.json").read_text(encoding="utf-8"))
            self.assertEqual(resolved_latest["snapshot_id"], "20260425T080300Z-sample-windows-codex")

            resolved_import = run_cli(mac_project, "import", "--tool", "codex", "--print-prompt")
            self.assertEqual(resolved_import.returncode, 0, resolved_import.stderr)
            self.assertIn("Windows exported offline before pulling", resolved_import.stdout)

        return None

    def test_doctor_reports_remote_branch_missing_and_latest_conflict(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            remote = tmp_path / "sync-state.git"
            project_root = tmp_path / "sample-project"

            self._init_bare_remote(remote)
            self._init_project(project_root, remote, device_id="sample-macbook")

            doctor_before_push = run_cli(project_root, "doctor", "--tool", "codex")
            self.assertEqual(doctor_before_push.returncode, 0, doctor_before_push.stderr)
            self.assertIn("Sidecar remote reachable: True", doctor_before_push.stdout)
            self.assertIn("Sidecar remote branch exists: False", doctor_before_push.stdout)
            self.assertIn("warning: sidecar remote branch does not exist yet", doctor_before_push.stdout)

            export = run_cli(
                project_root,
                "export",
                "--tool",
                "codex",
                "--goal",
                "Create the first branch",
                extra_env={
                    "AISS_DEVICE_ID": "sample-macbook",
                    "AISS_FIXED_NOW": "2026-04-25T08:00:00Z",
                },
            )
            self.assertEqual(export.returncode, 0, export.stderr)
            push = run_cli(project_root, "push", extra_env={"AISS_DEVICE_ID": "sample-macbook"})
            self.assertEqual(push.returncode, 0, push.stderr)

            latest_path = project_root / ".ai-session-sync" / "latest" / "codex.json"
            latest_path.write_text(
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

            doctor_conflict = run_cli(project_root, "doctor", "--tool", "codex")
            self.assertEqual(doctor_conflict.returncode, 0, doctor_conflict.stderr)
            self.assertIn("Latest state: conflict", doctor_conflict.stdout)
            self.assertIn("warning: latest pointer requires selection", doctor_conflict.stdout)
            self.assertIn("Run `aiss latest resolve --tool codex <snapshot_id>`.", doctor_conflict.stdout)

    def _init_bare_remote(self, remote: Path) -> None:
        remote.parent.mkdir(parents=True, exist_ok=True)
        init = run_command(remote.parent, "git", "init", "--bare", remote.name)
        self.assertEqual(init.returncode, 0, init.stderr)

    def _init_project(self, project_root: Path, remote: Path, *, device_id: str) -> None:
        project_root.mkdir(parents=True, exist_ok=True)
        init = run_cli(
            project_root,
            "init",
            "--backend",
            "git",
            "--storage",
            "sidecar-repo",
            "--remote",
            str(remote),
            "--branch",
            "main",
            extra_env={"AISS_DEVICE_ID": device_id},
        )
        self.assertEqual(init.returncode, 0, init.stderr)


if __name__ == "__main__":
    unittest.main()
