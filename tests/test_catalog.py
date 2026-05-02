from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from aiss.catalog import build_project_catalog, build_session_catalog, build_session_detail
from tests.cli_test_utils import run_cli
from tests.schema_utils import assert_matches_schema, load_schema


class CatalogTest(unittest.TestCase):
    def setUp(self) -> None:
        self.session_catalog_schema = load_schema("session-catalog.schema.json")
        self.session_detail_schema = load_schema("session-detail.schema.json")
        self.project_catalog_schema = load_schema("project-catalog.schema.json")

    def test_build_catalog_payloads_match_schemas(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            project_root = tmp_path / "repo"
            project_root.mkdir()
            codex_home = tmp_path / "codex-home"
            claude_home = tmp_path / "claude-home"

            codex_session_id = self._write_codex_transcript(
                codex_home,
                project_root,
                session_id="session-codex-1",
                title="Codex desktop catalog test",
                user_text="Continue implementing the desktop session catalog.",
                assistant_text="I am wiring session catalog, detail, and project views.",
                updated_at="2026-04-29T10:06:00Z",
            )
            claude_session_id = self._write_claude_transcript(
                claude_home,
                project_root,
                session_id="session-claude-1",
                title="Claude desktop catalog test",
                user_text="Cover the dirty patch replay state too.",
                assistant_text="I am validating the project catalog output.",
                updated_at="2026-04-29T10:12:00Z",
            )

            old_env = self._set_homes(codex_home, claude_home)
            try:
                session_catalog = build_session_catalog([project_root])
                assert_matches_schema(session_catalog, self.session_catalog_schema)
                self.assertEqual(len(session_catalog["sessions"]), 2)
                self.assertEqual(session_catalog["summary"]["tool_counts"], {"codex": 1, "claude": 1})

                codex_key = next(
                    entry["session_key"]
                    for entry in session_catalog["sessions"]
                    if entry["native_session_id"] == codex_session_id
                )
                claude_key = next(
                    entry["session_key"]
                    for entry in session_catalog["sessions"]
                    if entry["native_session_id"] == claude_session_id
                )

                codex_detail = build_session_detail(codex_key, [project_root])
                assert_matches_schema(codex_detail, self.session_detail_schema)
                self.assertIsNone(codex_detail["manifest"])
                self.assertEqual(codex_detail["provenance"]["manifest"], "missing")
                self.assertEqual(codex_detail["session"]["latest_state"], "missing")

                claude_detail = build_session_detail(claude_key, [project_root])
                assert_matches_schema(claude_detail, self.session_detail_schema)
                self.assertEqual(claude_detail["session"]["native_session_id"], claude_session_id)
                self.assertEqual(claude_detail["session"]["selected_excerpt_count"], 2)
                self.assertEqual(claude_detail["session"]["all_excerpt_count"], 2)

                project_catalog = build_project_catalog([project_root])
                assert_matches_schema(project_catalog, self.project_catalog_schema)
                self.assertEqual(project_catalog["summary"]["total_projects"], 1)
                self.assertEqual(project_catalog["summary"]["total_sessions"], 2)
                self.assertEqual(project_catalog["selected_project"]["session_count"], 2)
            finally:
                self._restore_env(old_env)

    def test_build_session_detail_links_manifest_handoff_and_patch_replay(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            project_root = tmp_path / "repo"
            project_root.mkdir()
            codex_home = tmp_path / "codex-home"

            session_id = self._write_codex_transcript(
                codex_home,
                project_root,
                session_id="session-linked",
                title="Linked snapshot session",
                user_text="Export a linked snapshot for desktop detail.",
                assistant_text="I will connect manifest, handoff, and patch replay.",
                updated_at="2026-04-29T11:05:00Z",
            )
            (project_root / "notes.txt").write_text("base line\npatch line\n", encoding="utf-8")

            old_env = self._set_homes(codex_home, None)
            try:
                init = run_cli(project_root, "init")
                self.assertEqual(init.returncode, 0, init.stderr)
                git_init = self._run(project_root, "git", "init")
                self.assertEqual(git_init.returncode, 0, git_init.stderr)
                self.assertEqual(self._run(project_root, "git", "config", "user.name", "AISS Test").returncode, 0)
                self.assertEqual(self._run(project_root, "git", "config", "user.email", "aiss@example.com").returncode, 0)
                self.assertEqual(self._run(project_root, "git", "add", "notes.txt").returncode, 0)
                self.assertEqual(self._run(project_root, "git", "commit", "-m", "base").returncode, 0)
                (project_root / "notes.txt").write_text("base line\npatch line\nmore local work\n", encoding="utf-8")

                export = run_cli(
                    project_root,
                    "export",
                    "--tool",
                    "codex",
                    "--include-patch",
                    extra_env={"AISS_FIXED_NOW": "2026-04-29T11:10:00Z"},
                )
                self.assertEqual(export.returncode, 0, export.stderr)

                catalog = build_session_catalog([project_root], include_claude=False)
                session_key = catalog["sessions"][0]["session_key"]
                detail = build_session_detail(session_key, [project_root], include_claude=False)
                assert_matches_schema(detail, self.session_detail_schema)
                self.assertIsNotNone(detail["manifest"])
                self.assertIsNotNone(detail["handoff"])
                self.assertEqual(detail["session"]["native_session_id"], session_id)
                self.assertEqual(detail["session"]["latest_state"], "ready")
                self.assertTrue(detail["session"]["has_handoff"])
                self.assertTrue(detail["session"]["has_patch"])
                self.assertIn("patch", detail["session"]["status_flags"])
                self.assertEqual(detail["provenance"]["manifest"], "source-of-truth")
                self.assertEqual(detail["patch_replay"]["state"], "unavailable")
                self.assertIsNone(detail["patch_replay"]["recommended_mode"])
                self.assertIn("Current worktree is dirty", detail["patch_replay"]["recommended_reason"])
                self.assertIn("Session Handoff", detail["handoff"]["markdown"])
            finally:
                self._restore_env(old_env)

    def test_project_catalog_surfaces_latest_conflict(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            project_root = tmp_path / "repo"
            project_root.mkdir()
            codex_home = tmp_path / "codex-home"

            self._write_codex_transcript(
                codex_home,
                project_root,
                session_id="session-conflict",
                title="Conflict session",
                user_text="Resolve latest conflict in the desktop project panel.",
                assistant_text="I will keep both candidate snapshots visible.",
                updated_at="2026-04-29T12:00:00Z",
            )

            old_env = self._set_homes(codex_home, None)
            try:
                init = run_cli(project_root, "init")
                self.assertEqual(init.returncode, 0, init.stderr)
                export = run_cli(
                    project_root,
                    "export",
                    "--tool",
                    "codex",
                    extra_env={"AISS_FIXED_NOW": "2026-04-29T12:10:00Z"},
                )
                self.assertEqual(export.returncode, 0, export.stderr)

                latest_path = project_root / ".ai-session-sync" / "latest" / "codex.json"
                latest_path.write_text(
                    json.dumps(
                        {
                            "requires_selection": True,
                            "candidates": [
                                "20260429T121500Z-device-b-codex",
                                "20260429T121000Z-device-a-codex",
                            ],
                        },
                        indent=2,
                    )
                    + "\n",
                    encoding="utf-8",
                )

                session_catalog = build_session_catalog([project_root], include_claude=False)
                assert_matches_schema(session_catalog, self.session_catalog_schema)
                self.assertEqual(session_catalog["sessions"][0]["latest_state"], "conflict")
                self.assertIn("conflict", session_catalog["sessions"][0]["status_flags"])

                session_key = session_catalog["sessions"][0]["session_key"]
                detail = build_session_detail(session_key, [project_root], include_claude=False)
                assert_matches_schema(detail, self.session_detail_schema)
                self.assertEqual(
                    detail["session"]["latest_candidates"],
                    ["20260429T121500Z-device-b-codex", "20260429T121000Z-device-a-codex"],
                )

                project_catalog = build_project_catalog([project_root], include_claude=False)
                assert_matches_schema(project_catalog, self.project_catalog_schema)
                self.assertEqual(project_catalog["summary"]["latest_conflict_count"], 1)
                self.assertEqual(
                    project_catalog["selected_project"]["latest_conflicts"]["codex"],
                    ["20260429T121500Z-device-b-codex", "20260429T121000Z-device-a-codex"],
                )
                self.assertEqual(
                    project_catalog["selected_project"]["recommended_session_key"],
                    session_key,
                )
            finally:
                self._restore_env(old_env)

    def _write_codex_transcript(
        self,
        codex_home: Path,
        project_root: Path,
        *,
        session_id: str,
        title: str,
        user_text: str,
        assistant_text: str,
        updated_at: str,
    ) -> str:
        sessions_dir = codex_home / "sessions" / "2026" / "04" / "29"
        sessions_dir.mkdir(parents=True, exist_ok=True)
        (codex_home / "session_index.jsonl").write_text(
            json.dumps({"id": session_id, "thread_name": title, "updated_at": updated_at}, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        transcript = sessions_dir / f"rollout-{session_id}.jsonl"
        transcript.write_text(
            "\n".join(
                [
                    json.dumps(
                        {
                            "timestamp": "2026-04-29T10:00:00Z",
                            "type": "session_meta",
                            "payload": {"id": session_id, "cwd": str(project_root)},
                        },
                        ensure_ascii=False,
                    ),
                    json.dumps(
                        {
                            "timestamp": "2026-04-29T10:01:00Z",
                            "type": "response_item",
                            "payload": {
                                "type": "message",
                                "role": "user",
                                "content": [{"type": "input_text", "text": user_text}],
                            },
                        },
                        ensure_ascii=False,
                    ),
                    json.dumps(
                        {
                            "timestamp": updated_at,
                            "type": "response_item",
                            "payload": {
                                "type": "message",
                                "role": "assistant",
                                "content": [{"type": "output_text", "text": assistant_text}],
                            },
                        },
                        ensure_ascii=False,
                    ),
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        return session_id

    def _write_claude_transcript(
        self,
        claude_home: Path,
        project_root: Path,
        *,
        session_id: str,
        title: str,
        user_text: str,
        assistant_text: str,
        updated_at: str,
    ) -> str:
        transcript_dir = claude_home / "projects" / "desktop-test"
        transcript_dir.mkdir(parents=True, exist_ok=True)
        transcript = transcript_dir / f"{title}.jsonl"
        transcript.write_text(
            "\n".join(
                [
                    json.dumps(
                        {
                            "type": "user",
                            "timestamp": "2026-04-29T10:10:00Z",
                            "cwd": str(project_root),
                            "sessionId": session_id,
                            "message": {"role": "user", "content": [{"type": "text", "text": user_text}]},
                        },
                        ensure_ascii=False,
                    ),
                    json.dumps(
                        {
                            "type": "assistant",
                            "timestamp": updated_at,
                            "cwd": str(project_root),
                            "sessionId": session_id,
                            "message": {
                                "role": "assistant",
                                "content": [{"type": "text", "text": assistant_text}],
                            },
                        },
                        ensure_ascii=False,
                    ),
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        return session_id

    def _set_homes(self, codex_home: Path | None, claude_home: Path | None) -> dict[str, str | None]:
        old = {
            "AISS_CODEX_HOME": os.environ.get("AISS_CODEX_HOME"),
            "AISS_CLAUDE_HOME": os.environ.get("AISS_CLAUDE_HOME"),
        }
        if codex_home is None:
            os.environ.pop("AISS_CODEX_HOME", None)
        else:
            os.environ["AISS_CODEX_HOME"] = str(codex_home)
        if claude_home is None:
            os.environ.pop("AISS_CLAUDE_HOME", None)
        else:
            os.environ["AISS_CLAUDE_HOME"] = str(claude_home)
        return old

    def _restore_env(self, old: dict[str, str | None]) -> None:
        for key, value in old.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def _run(self, cwd: Path, *args: str):
        import subprocess

        return subprocess.run(
            list(args),
            cwd=cwd,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )


if __name__ == "__main__":
    unittest.main()
