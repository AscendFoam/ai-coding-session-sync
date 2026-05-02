from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from aiss.api import BundleRequest, SessionQuery, get_desktop_ui_bundle, get_health, get_projects, get_session_detail, get_sessions, rescan_sessions
from tests.schema_utils import assert_matches_schema, load_schema


class ApiTest(unittest.TestCase):
    def setUp(self) -> None:
        self.session_catalog_schema = load_schema("session-catalog.schema.json")
        self.session_detail_schema = load_schema("session-detail.schema.json")
        self.project_catalog_schema = load_schema("project-catalog.schema.json")
        self.desktop_ui_bundle_schema = load_schema("desktop-ui-bundle.schema.json")

    def test_get_health_reports_project_roots(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_root = Path(tmp) / "repo"
            project_root.mkdir()
            payload = get_health([project_root])
            self.assertTrue(payload["ok"])
            self.assertEqual(payload["project_count"], 1)
            self.assertEqual(payload["project_roots"], [project_root.resolve().as_posix()])

    def test_get_sessions_and_projects_support_filtering(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            project_root = tmp_path / "repo"
            project_root.mkdir()
            codex_home = tmp_path / "codex-home"
            claude_home = tmp_path / "claude-home"

            self._write_codex_transcript(
                codex_home,
                project_root,
                session_id="session-codex-filter",
                title="Codex filter test",
                user_text="Review conflict handling for the desktop library.",
                assistant_text="I am keeping the Codex session available for filtering.",
                updated_at="2026-04-29T13:00:00Z",
            )
            self._write_claude_transcript(
                claude_home,
                project_root,
                session_id="session-claude-filter",
                title="Claude filter test",
                user_text="Cover dirty state in the session library.",
                assistant_text="I am validating patch replay badges for the frontend.",
                updated_at="2026-04-29T13:05:00Z",
            )

            old_env = self._set_homes(codex_home, claude_home)
            try:
                sessions = get_sessions([project_root])
                assert_matches_schema(sessions, self.session_catalog_schema)
                self.assertEqual(len(sessions["sessions"]), 2)

                codex_only = get_sessions([project_root], query=SessionQuery(tool="codex"))
                assert_matches_schema(codex_only, self.session_catalog_schema)
                self.assertEqual(len(codex_only["sessions"]), 1)
                self.assertEqual(codex_only["sessions"][0]["tool"], "codex")

                search = get_sessions([project_root], query=SessionQuery(q="dirty"))
                assert_matches_schema(search, self.session_catalog_schema)
                self.assertEqual(len(search["sessions"]), 1)
                self.assertEqual(search["sessions"][0]["tool"], "claude")

                projects = get_projects([project_root], query=SessionQuery(tool="claude"))
                assert_matches_schema(projects, self.project_catalog_schema)
                self.assertEqual(projects["summary"]["tool_counts"], {"codex": 0, "claude": 1})
                self.assertEqual(projects["selected_project"]["active_tools"], ["claude"])
            finally:
                self._restore_env(old_env)

    def test_get_session_detail_and_bundle_match_schemas(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            project_root = tmp_path / "repo"
            project_root.mkdir()
            codex_home = tmp_path / "codex-home"

            self._write_codex_transcript(
                codex_home,
                project_root,
                session_id="session-bundle",
                title="Bundle session test",
                user_text="Generate a desktop UI bundle for the frontend.",
                assistant_text="I will keep the selected session detail embedded.",
                updated_at="2026-04-29T13:20:00Z",
            )

            old_env = self._set_homes(codex_home, None)
            try:
                sessions = get_sessions([project_root])
                session_key = sessions["sessions"][0]["session_key"]

                detail = get_session_detail(session_key, [project_root])
                assert_matches_schema(detail, self.session_detail_schema)
                self.assertEqual(detail["session"]["session_key"], session_key)

                bundle = get_desktop_ui_bundle(
                    [project_root],
                    request=BundleRequest(
                        selected_session_key=session_key,
                        selected_project_id="repo",
                        active_view="session-detail",
                        filters=SessionQuery(tool="all", project_id="repo", sort="updated_at", order="desc"),
                    ),
                )
                assert_matches_schema(bundle, self.desktop_ui_bundle_schema)
                self.assertEqual(bundle["selected_session_detail"]["session"]["session_key"], session_key)
                self.assertEqual(bundle["view_state"]["active_view"], "session-detail")
                self.assertEqual(bundle["view_state"]["selected_session_key"], session_key)
                self.assertEqual(bundle["view_state"]["filters"]["project_id"], "repo")
            finally:
                self._restore_env(old_env)

    def test_rescan_sessions_wraps_session_catalog(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            project_root = tmp_path / "repo"
            project_root.mkdir()
            codex_home = tmp_path / "codex-home"

            self._write_codex_transcript(
                codex_home,
                project_root,
                session_id="session-rescan",
                title="Rescan test",
                user_text="Rescan the current sessions.",
                assistant_text="I am returning the refreshed session catalog.",
                updated_at="2026-04-29T13:40:00Z",
            )

            old_env = self._set_homes(codex_home, None)
            try:
                payload = rescan_sessions([project_root], query=SessionQuery(tool="codex"))
                self.assertTrue(payload["ok"])
                assert_matches_schema(payload["session_catalog"], self.session_catalog_schema)
                self.assertEqual(len(payload["session_catalog"]["sessions"]), 1)
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
    ) -> None:
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
                            "timestamp": "2026-04-29T13:00:00Z",
                            "type": "session_meta",
                            "payload": {"id": session_id, "cwd": str(project_root)},
                        },
                        ensure_ascii=False,
                    ),
                    json.dumps(
                        {
                            "timestamp": "2026-04-29T13:01:00Z",
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
    ) -> None:
        transcript_dir = claude_home / "projects" / "api-test"
        transcript_dir.mkdir(parents=True, exist_ok=True)
        transcript = transcript_dir / f"{title}.jsonl"
        transcript.write_text(
            "\n".join(
                [
                    json.dumps(
                        {
                            "type": "user",
                            "timestamp": "2026-04-29T13:02:00Z",
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


if __name__ == "__main__":
    unittest.main()
