from __future__ import annotations

import json
import os
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from aiss.api import create_api_server


class ApiServerTest(unittest.TestCase):
    def test_http_routes_return_expected_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            project_root = tmp_path / "repo"
            project_root.mkdir()
            codex_home = tmp_path / "codex-home"
            self._write_codex_transcript(
                codex_home,
                project_root,
                session_id="session-http",
                title="HTTP session test",
                user_text="Serve the desktop API over localhost.",
                assistant_text="I am exposing the session catalog over JSON.",
                updated_at="2026-04-29T15:00:00Z",
            )

            old_env = self._set_codex_home(codex_home)
            server = create_api_server([project_root], host="127.0.0.1", port=0)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                base_url = f"http://127.0.0.1:{server.server_address[1]}"

                health = self._get_json(f"{base_url}/api/health")
                self.assertTrue(health["ok"])
                self.assertEqual(health["project_count"], 1)

                meta = self._get_json(f"{base_url}/api/meta")
                self.assertEqual(meta["api"], "desktop-json-server")
                self.assertIn("codex", meta["supported_tools"])

                sessions = self._get_json(f"{base_url}/api/sessions?tool=codex")
                self.assertEqual(len(sessions["sessions"]), 1)
                session_key = sessions["sessions"][0]["session_key"]

                detail = self._get_json(f"{base_url}/api/sessions/{session_key}")
                self.assertEqual(detail["session"]["session_key"], session_key)

                projects = self._get_json(f"{base_url}/api/projects")
                self.assertEqual(projects["summary"]["total_projects"], 1)
                project_id = projects["selected_project"]["project_id"]

                project_detail = self._get_json(f"{base_url}/api/projects/{project_id}")
                self.assertEqual(project_detail["selected_project"]["project_id"], project_id)

                bundle = self._get_json(
                    f"{base_url}/api/ui-bundle?tool=codex&selected_session_key={session_key}&active_view=session-detail"
                )
                self.assertEqual(bundle["selected_session_detail"]["session"]["session_key"], session_key)
                self.assertEqual(bundle["view_state"]["active_view"], "session-detail")

                fixture_index = self._get_json(f"{base_url}/api/dev/fixture-index")
                self.assertIn("desktop", fixture_index["fixture_groups"])
                self.assertIn("sample-desktop-ui-bundle.json", fixture_index["fixture_groups"]["desktop"])

                fixture = self._get_json(f"{base_url}/api/dev/fixture/sample-desktop-ui-bundle.json")
                self.assertEqual(fixture["format"], "json")
                self.assertEqual(fixture["payload"]["bundle_id"], "desktop-sample-bundle")

                rescan = self._post_json(
                    f"{base_url}/api/sessions/rescan",
                    {"tools": ["codex"]},
                )
                self.assertTrue(rescan["ok"])
                self.assertEqual(rescan["rescanned_tools"], ["codex"])
                self.assertEqual(rescan["session_count"], 1)

                with self.assertRaises(HTTPError) as missing_ctx:
                    self._get_json(f"{base_url}/api/does-not-exist")
                self.assertEqual(missing_ctx.exception.code, 404)
            finally:
                server.shutdown()
                thread.join(timeout=5)
                server.server_close()
                self._restore_env(old_env)

    def _get_json(self, url: str) -> dict[str, object]:
        with urlopen(url) as response:
            return json.loads(response.read().decode("utf-8"))

    def _post_json(self, url: str, payload: dict[str, object]) -> dict[str, object]:
        request = Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request) as response:
            return json.loads(response.read().decode("utf-8"))

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
                            "timestamp": "2026-04-29T14:58:00Z",
                            "type": "session_meta",
                            "payload": {"id": session_id, "cwd": str(project_root)},
                        },
                        ensure_ascii=False,
                    ),
                    json.dumps(
                        {
                            "timestamp": "2026-04-29T14:59:00Z",
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

    def _set_codex_home(self, codex_home: Path) -> str | None:
        old = os.environ.get("AISS_CODEX_HOME")
        os.environ["AISS_CODEX_HOME"] = str(codex_home)
        return old

    def _restore_env(self, old: str | None) -> None:
        if old is None:
            os.environ.pop("AISS_CODEX_HOME", None)
        else:
            os.environ["AISS_CODEX_HOME"] = old


if __name__ == "__main__":
    unittest.main()
