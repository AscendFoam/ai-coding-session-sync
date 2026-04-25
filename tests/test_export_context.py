from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


def run_cli(tmp_path: Path, *args: str, extra_env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1] / "src")
    if extra_env:
        env.update(extra_env)
    return subprocess.run(
        [sys.executable, "-m", "aiss", *args],
        cwd=tmp_path,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        env=env,
    )


class ExportContextTest(unittest.TestCase):
    def test_codex_export_extracts_recent_transcript(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_root = Path(tmp) / "repo"
            project_root.mkdir()
            codex_home = Path(tmp) / "codex-home"
            sessions_dir = codex_home / "sessions" / "2026" / "04" / "23"
            sessions_dir.mkdir(parents=True)
            (codex_home / "session_index.jsonl").write_text(
                json.dumps(
                    {
                        "id": "session-123",
                        "thread_name": "Implement export transcript extraction",
                        "updated_at": "2026-04-23T07:30:00Z",
                    },
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )
            transcript = sessions_dir / "rollout-2026-04-23T07-28-51-session-123.jsonl"
            transcript.write_text(
                "\n".join(
                    [
                        json.dumps(
                            {
                                "timestamp": "2026-04-23T07:28:51.399Z",
                                "type": "session_meta",
                                "payload": {
                                    "id": "session-123",
                                    "cwd": str(project_root),
                                },
                            },
                            ensure_ascii=False,
                        ),
                        json.dumps(
                            {
                                "timestamp": "2026-04-23T07:28:51.400Z",
                                "type": "response_item",
                                "payload": {
                                    "type": "message",
                                    "role": "user",
                                    "content": [
                                        {
                                            "type": "input_text",
                                            "text": f"请继续处理 {project_root.as_posix()}/docs/spec.md，并实现真正的 transcript extraction。",
                                        }
                                    ],
                                },
                            },
                            ensure_ascii=False,
                        ),
                        json.dumps(
                            {
                                "timestamp": "2026-04-23T07:29:02.400Z",
                                "type": "response_item",
                                "payload": {
                                    "type": "message",
                                    "role": "assistant",
                                    "content": [
                                        {
                                            "type": "output_text",
                                            "text": "我会先读取本地 Codex transcript，再把 export 改成自动抽取最近上下文。",
                                        }
                                    ],
                                },
                            },
                            ensure_ascii=False,
                        ),
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            export = run_cli(project_root, "export", "--tool", "codex", extra_env={"AISS_CODEX_HOME": str(codex_home)})
            self.assertEqual(export.returncode, 0, export.stderr)

            latest = json.loads((project_root / ".ai-session-sync" / "latest" / "codex.json").read_text(encoding="utf-8"))
            manifest = json.loads((project_root / ".ai-session-sync" / latest["manifest"]).read_text(encoding="utf-8"))
            self.assertEqual(manifest["source"]["contexts"][0]["session_id"], "session-123")

            handoff = (project_root / ".ai-session-sync" / manifest["artifacts"]["handoff"]).read_text(encoding="utf-8")
            excerpts = (project_root / ".ai-session-sync" / manifest["artifacts"]["recent_turns"]).read_text(encoding="utf-8")
            self.assertIn("Implement export transcript extraction", handoff)
            self.assertIn("请继续处理 ${PROJECT_ROOT}/docs/spec.md", handoff)
            self.assertIn("自动抽取最近上下文", excerpts)
            self.assertNotIn(project_root.as_posix(), excerpts)

    def test_claude_export_extracts_recent_transcript(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_root = Path(tmp) / "repo"
            project_root.mkdir()
            claude_home = Path(tmp) / "claude-home"
            project_dir = claude_home / "projects" / "-tmp-repo"
            project_dir.mkdir(parents=True)
            transcript = project_dir / "session-claude.jsonl"
            transcript.write_text(
                "\n".join(
                    [
                        json.dumps(
                            {
                                "type": "user",
                                "message": {
                                    "role": "user",
                                    "content": [{"type": "text", "text": "请继续实现 Claude transcript extraction。"}],
                                },
                                "timestamp": "2026-04-23T08:00:00Z",
                                "cwd": str(project_root),
                                "sessionId": "session-claude",
                            },
                            ensure_ascii=False,
                        ),
                        json.dumps(
                            {
                                "type": "assistant",
                                "message": {
                                    "role": "assistant",
                                    "content": [
                                        {"type": "thinking", "thinking": "hidden"},
                                        {"type": "text", "text": "我会优先读取项目 transcript，并过滤 tool_use 和 thinking。"},
                                    ],
                                },
                                "timestamp": "2026-04-23T08:00:05Z",
                                "cwd": str(project_root),
                                "sessionId": "session-claude",
                            },
                            ensure_ascii=False,
                        ),
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            export = run_cli(project_root, "export", "--tool", "claude", extra_env={"AISS_CLAUDE_HOME": str(claude_home)})
            self.assertEqual(export.returncode, 0, export.stderr)

            latest = json.loads((project_root / ".ai-session-sync" / "latest" / "claude.json").read_text(encoding="utf-8"))
            manifest = json.loads((project_root / ".ai-session-sync" / latest["manifest"]).read_text(encoding="utf-8"))
            handoff = (project_root / ".ai-session-sync" / manifest["artifacts"]["handoff"]).read_text(encoding="utf-8")
            excerpts = (project_root / ".ai-session-sync" / manifest["artifacts"]["recent_turns"]).read_text(encoding="utf-8")

            self.assertEqual(manifest["source"]["contexts"][0]["session_id"], "session-claude")
            self.assertIn("请继续实现 Claude transcript extraction", handoff)
            self.assertIn("过滤 tool_use 和 thinking", excerpts)
            self.assertNotIn("hidden", excerpts)


if __name__ == "__main__":
    unittest.main()
