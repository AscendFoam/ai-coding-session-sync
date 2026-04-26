from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tests.cli_test_utils import run_cli, run_command


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
            self.assertIn("Patch status: no patch artifact was exported for this snapshot.", imported.stdout)
            self.assertIn("Ship the MVP handoff flow", imported.stdout)
            self.assertIn("不要假设可以原生恢复同一个 session", imported.stdout)

    def test_import_reports_patch_guidance_and_applies_clean_patch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            repo.mkdir()
            self._init_git_repo(repo)

            init = run_cli(repo, "init")
            self.assertEqual(init.returncode, 0, init.stderr)

            notes_path = repo / "notes.txt"
            notes_path.write_text("base line\npatch line\n", encoding="utf-8")

            export = run_cli(
                repo,
                "export",
                "--tool",
                "codex",
                "--goal",
                "Carry the uncommitted patch forward",
                "--include-patch",
                extra_env={
                    "AISS_DEVICE_ID": "sample-macbook",
                    "AISS_FIXED_NOW": "2026-04-25T09:00:00Z",
                },
            )
            self.assertEqual(export.returncode, 0, export.stderr)

            snapshot_id = "20260425T090000Z-sample-macbook-codex"
            manifest = self._load_manifest(repo, "codex")
            self.assertEqual(manifest["snapshot_id"], snapshot_id)
            self.assertEqual(manifest["artifacts"]["patch"], f"patches/{snapshot_id}.patch")

            restore = run_command(repo, "git", "checkout", "--", "notes.txt")
            self.assertEqual(restore.returncode, 0, restore.stderr)

            imported = run_cli(repo, "import", "--tool", "codex", "--snapshot", snapshot_id, "--print-prompt")
            self.assertEqual(imported.returncode, 0, imported.stderr)
            self.assertIn(f"Patch status: `patches/{snapshot_id}.patch`", imported.stdout)
            self.assertIn("- Export branch: `main`", imported.stdout)
            self.assertIn("- Current branch: `main`", imported.stdout)
            self.assertIn("- `git apply --check` succeeded.", imported.stdout)
            self.assertIn(
                f"- Safe path: run `aiss import --tool codex --snapshot {snapshot_id} --apply-patch` if you want to replay the uncommitted work now.",
                imported.stdout,
            )

            applied = run_cli(repo, "import", "--tool", "codex", "--snapshot", snapshot_id, "--apply-patch")
            self.assertEqual(applied.returncode, 0, applied.stderr)
            self.assertIn("Patch applied successfully.", applied.stdout)
            self.assertEqual(notes_path.read_text(encoding="utf-8"), "base line\npatch line\n")

    def test_import_refuses_apply_patch_on_dirty_worktree(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            repo.mkdir()
            self._init_git_repo(repo)

            init = run_cli(repo, "init")
            self.assertEqual(init.returncode, 0, init.stderr)

            snapshot_id = self._export_patch_snapshot(repo)

            restore = run_command(repo, "git", "checkout", "--", "notes.txt")
            self.assertEqual(restore.returncode, 0, restore.stderr)
            (repo / "notes.txt").write_text("base line\nlocal dirty edit\n", encoding="utf-8")

            imported = run_cli(repo, "import", "--tool", "codex", "--snapshot", snapshot_id, "--apply-patch")
            self.assertNotEqual(imported.returncode, 0)
            combined = f"{imported.stdout}\n{imported.stderr}"
            self.assertIn("Current worktree dirty: True", imported.stdout)
            self.assertIn("- `git apply --check` failed:", imported.stdout)
            self.assertIn("Refusing to apply patch to a dirty worktree.", combined)

    def test_import_can_apply_patch_with_allow_dirty(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            repo.mkdir()
            self._init_git_repo(repo)

            init = run_cli(repo, "init")
            self.assertEqual(init.returncode, 0, init.stderr)

            snapshot_id = self._export_patch_snapshot(repo)

            restore = run_command(repo, "git", "checkout", "--", "notes.txt")
            self.assertEqual(restore.returncode, 0, restore.stderr)
            (repo / "scratch.txt").write_text("scratch base\nlocal dirty change\n", encoding="utf-8")

            applied = run_cli(
                repo,
                "import",
                "--tool",
                "codex",
                "--snapshot",
                snapshot_id,
                "--apply-patch",
                "--allow-dirty",
            )
            self.assertEqual(applied.returncode, 0, applied.stderr)
            self.assertIn("Patch applied successfully.", applied.stdout)
            self.assertIn("Applied with --allow-dirty", applied.stdout)
            self.assertEqual((repo / "notes.txt").read_text(encoding="utf-8"), "base line\npatch line\n")
            self.assertEqual((repo / "scratch.txt").read_text(encoding="utf-8"), "scratch base\nlocal dirty change\n")

    def test_import_suggests_allow_dirty_when_patch_is_clean_but_worktree_is_dirty(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            repo.mkdir()
            self._init_git_repo(repo)

            init = run_cli(repo, "init")
            self.assertEqual(init.returncode, 0, init.stderr)

            snapshot_id = self._export_patch_snapshot(repo)

            restore = run_command(repo, "git", "checkout", "--", "notes.txt")
            self.assertEqual(restore.returncode, 0, restore.stderr)
            (repo / "scratch.txt").write_text("scratch base\nlocal dirty change\n", encoding="utf-8")

            imported = run_cli(repo, "import", "--tool", "codex", "--snapshot", snapshot_id, "--print-prompt")
            self.assertEqual(imported.returncode, 0, imported.stderr)
            self.assertIn("Current worktree dirty: True", imported.stdout)
            self.assertIn("- `git apply --check` succeeded.", imported.stdout)
            self.assertIn(
                f"`aiss import --tool codex --snapshot {snapshot_id} --apply-patch --allow-dirty`",
                imported.stdout,
            )

    def test_import_reports_check_failure_when_head_has_moved(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            repo.mkdir()
            self._init_git_repo(repo)

            init = run_cli(repo, "init")
            self.assertEqual(init.returncode, 0, init.stderr)

            snapshot_id = self._export_patch_snapshot(repo)

            restore = run_command(repo, "git", "checkout", "--", "notes.txt")
            self.assertEqual(restore.returncode, 0, restore.stderr)
            (repo / "notes.txt").write_text("conflicting rewrite\n", encoding="utf-8")
            commit = run_command(repo, "git", "commit", "-am", "rewrite notes")
            self.assertEqual(commit.returncode, 0, commit.stderr)

            imported = run_cli(repo, "import", "--tool", "codex", "--snapshot", snapshot_id, "--print-prompt")
            self.assertEqual(imported.returncode, 0, imported.stderr)
            self.assertIn("- HEAD differs from the export snapshot.", imported.stdout)
            self.assertIn("- `git apply --check` failed:", imported.stdout)
            self.assertIn("Review the handoff first; patch replay is not safe until the mismatch is resolved.", imported.stdout)

            apply_attempt = run_cli(repo, "import", "--tool", "codex", "--snapshot", snapshot_id, "--apply-patch")
            self.assertNotEqual(apply_attempt.returncode, 0)
            combined = f"{apply_attempt.stdout}\n{apply_attempt.stderr}"
            self.assertIn("Patch does not apply cleanly:", combined)

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

    def _init_git_repo(self, repo: Path) -> None:
        init = run_command(repo, "git", "init")
        self.assertEqual(init.returncode, 0, init.stderr)
        config_name = run_command(repo, "git", "config", "user.name", "AISS Test")
        self.assertEqual(config_name.returncode, 0, config_name.stderr)
        config_email = run_command(repo, "git", "config", "user.email", "aiss@example.com")
        self.assertEqual(config_email.returncode, 0, config_email.stderr)
        checkout = run_command(repo, "git", "checkout", "-b", "main")
        self.assertEqual(checkout.returncode, 0, checkout.stderr)
        (repo / ".gitignore").write_text(".ai-session-sync/\n", encoding="utf-8")
        (repo / "notes.txt").write_text("base line\n", encoding="utf-8")
        (repo / "scratch.txt").write_text("scratch base\n", encoding="utf-8")
        add = run_command(repo, "git", "add", ".")
        self.assertEqual(add.returncode, 0, add.stderr)
        commit = run_command(repo, "git", "commit", "-m", "initial")
        self.assertEqual(commit.returncode, 0, commit.stderr)

    def _export_patch_snapshot(self, repo: Path) -> str:
        (repo / "notes.txt").write_text("base line\npatch line\n", encoding="utf-8")
        export = run_cli(
            repo,
            "export",
            "--tool",
            "codex",
            "--goal",
            "Carry the uncommitted patch forward",
            "--include-patch",
            extra_env={
                "AISS_DEVICE_ID": "sample-macbook",
                "AISS_FIXED_NOW": "2026-04-25T09:00:00Z",
            },
        )
        self.assertEqual(export.returncode, 0, export.stderr)
        return "20260425T090000Z-sample-macbook-codex"

    def _load_manifest(self, repo: Path, tool: str) -> dict[str, object]:
        latest = json.loads((repo / ".ai-session-sync" / "latest" / f"{tool}.json").read_text(encoding="utf-8"))
        return json.loads((repo / ".ai-session-sync" / latest["manifest"]).read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
