from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from urllib.request import urlopen


class ServeCliTest(unittest.TestCase):
    def test_aiss_serve_exposes_health_endpoint(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            project_root = tmp_path / "repo"
            project_root.mkdir()
            codex_home = tmp_path / "codex-home"
            self._write_codex_transcript(
                codex_home,
                project_root,
                session_id="session-cli-serve",
                title="Serve CLI test",
                user_text="Start the local desktop API server.",
                assistant_text="I am exposing the health endpoint over localhost.",
                updated_at="2026-04-29T16:00:00Z",
            )

            port = self._free_port()
            env = os.environ.copy()
            env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1] / "src")
            env["AISS_CODEX_HOME"] = str(codex_home)

            process = subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "aiss",
                    "serve",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    str(port),
                    "--project-root",
                    str(project_root),
                ],
                cwd=project_root,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=env,
            )
            try:
                self._wait_for_server(port)
                with urlopen(f"http://127.0.0.1:{port}/api/health") as response:
                    payload = json.loads(response.read().decode("utf-8"))
                self.assertTrue(payload["ok"])
                self.assertEqual(payload["project_count"], 1)
            finally:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)

    def _wait_for_server(self, port: int, *, timeout: float = 5.0) -> None:
        deadline = time.time() + timeout
        url = f"http://127.0.0.1:{port}/api/health"
        last_error: Exception | None = None
        while time.time() < deadline:
            try:
                with urlopen(url):
                    return
            except Exception as exc:  # pragma: no cover - short retry loop
                last_error = exc
                time.sleep(0.1)
        raise AssertionError(f"Server did not become ready on port {port}: {last_error}")

    def _free_port(self) -> int:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(("127.0.0.1", 0))
            return int(sock.getsockname()[1])

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
                            "timestamp": "2026-04-29T15:58:00Z",
                            "type": "session_meta",
                            "payload": {"id": session_id, "cwd": str(project_root)},
                        },
                        ensure_ascii=False,
                    ),
                    json.dumps(
                        {
                            "timestamp": "2026-04-29T15:59:00Z",
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


if __name__ == "__main__":
    unittest.main()
