from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tests.cli_test_utils import run_cli, transcript_timestamp


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
            self.assertIn("score", manifest["source"]["contexts"][0])
            self.assertIn("goal_candidate", manifest["source"]["contexts"][0])
            self.assertIn("score_reasons", manifest["source"]["contexts"][0])
            self.assertIn("total_excerpt_count", manifest["source"]["contexts"][0])

            handoff = (project_root / ".ai-session-sync" / manifest["artifacts"]["handoff"]).read_text(encoding="utf-8")
            excerpts = (project_root / ".ai-session-sync" / manifest["artifacts"]["recent_turns"]).read_text(encoding="utf-8")
            self.assertIn("Implement export transcript extraction", handoff)
            self.assertIn("请继续处理 ${PROJECT_ROOT}/docs/spec.md", handoff)
            self.assertIn("自动抽取最近上下文", excerpts)
            self.assertNotIn(project_root.as_posix(), excerpts)

    def test_codex_export_keeps_latest_user_goal_when_tail_is_assistant_heavy(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_root = Path(tmp) / "repo"
            project_root.mkdir()
            codex_home = Path(tmp) / "codex-home"
            sessions_dir = codex_home / "sessions" / "2026" / "04" / "25"
            sessions_dir.mkdir(parents=True)
            (codex_home / "session_index.jsonl").write_text(
                json.dumps(
                    {
                        "id": "session-heavy",
                        "thread_name": "Improve goal extraction",
                        "updated_at": "2026-04-25T06:00:00Z",
                    },
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )
            records = [
                {
                    "timestamp": "2026-04-25T05:50:00Z",
                    "type": "session_meta",
                    "payload": {"id": "session-heavy", "cwd": str(project_root)},
                },
                {
                    "timestamp": "2026-04-25T05:51:00Z",
                    "type": "response_item",
                    "payload": {
                        "type": "message",
                        "role": "user",
                        "content": [
                            {
                                "type": "input_text",
                                "text": (
                                    "# Context from my IDE setup:\n\n"
                                    "## My request for Codex:\n"
                                    "继续把 adapter 做厚一点：优先修 goal 提炼和 session ranking，再补一个 inspect。"
                                ),
                            }
                        ],
                    },
                },
            ]
            for index in range(12):
                records.append(
                    {
                        "timestamp": transcript_timestamp(start_minute=52, offset=index),
                        "type": "response_item",
                        "payload": {
                            "type": "message",
                            "role": "assistant",
                            "content": [
                                {
                                    "type": "output_text",
                                    "text": f"assistant progress update {index}",
                                }
                            ],
                        },
                    }
                )
            transcript = sessions_dir / "rollout-heavy.jsonl"
            transcript.write_text("\n".join(json.dumps(record, ensure_ascii=False) for record in records) + "\n", encoding="utf-8")

            export = run_cli(project_root, "export", "--tool", "codex", extra_env={"AISS_CODEX_HOME": str(codex_home)})
            self.assertEqual(export.returncode, 0, export.stderr)

            latest = json.loads((project_root / ".ai-session-sync" / "latest" / "codex.json").read_text(encoding="utf-8"))
            manifest = json.loads((project_root / ".ai-session-sync" / latest["manifest"]).read_text(encoding="utf-8"))
            handoff = (project_root / ".ai-session-sync" / manifest["artifacts"]["handoff"]).read_text(encoding="utf-8")
            excerpts = (project_root / ".ai-session-sync" / manifest["artifacts"]["recent_turns"]).read_text(encoding="utf-8")

            self.assertIn("继续把 adapter 做厚一点：优先修 goal 提炼和 session ranking，再补一个 inspect。", handoff)
            self.assertIn('"role": "user"', excerpts)
            self.assertIn("assistant progress update 11", excerpts)

    def test_codex_inspect_prefers_better_matching_session(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_root = Path(tmp) / "repo"
            project_root.mkdir()
            other_root = Path(tmp) / "other"
            other_root.mkdir()
            codex_home = Path(tmp) / "codex-home"
            sessions_dir = codex_home / "sessions" / "2026" / "04" / "25"
            sessions_dir.mkdir(parents=True)
            (codex_home / "session_index.jsonl").write_text(
                "\n".join(
                    [
                        json.dumps({"id": "weak", "thread_name": "Weak match", "updated_at": "2026-04-25T06:10:00Z"}, ensure_ascii=False),
                        json.dumps({"id": "strong", "thread_name": "Strong match", "updated_at": "2026-04-25T06:09:00Z"}, ensure_ascii=False),
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            weak = sessions_dir / "weak.jsonl"
            weak.write_text(
                "\n".join(
                    [
                        json.dumps({"timestamp": "2026-04-25T06:09:00Z", "type": "session_meta", "payload": {"id": "weak", "cwd": str(other_root)}}, ensure_ascii=False),
                        json.dumps(
                            {
                                "timestamp": "2026-04-25T06:09:30Z",
                                "type": "response_item",
                                "payload": {
                                    "type": "message",
                                    "role": "user",
                                    "content": [{"type": "input_text", "text": "weak request"}],
                                },
                            },
                            ensure_ascii=False,
                        ),
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            strong = sessions_dir / "strong.jsonl"
            strong.write_text(
                "\n".join(
                    [
                        json.dumps({"timestamp": "2026-04-25T06:08:00Z", "type": "session_meta", "payload": {"id": "strong", "cwd": str(project_root)}}, ensure_ascii=False),
                        json.dumps(
                            {
                                "timestamp": "2026-04-25T06:08:30Z",
                                "type": "response_item",
                                "payload": {
                                    "type": "message",
                                    "role": "user",
                                    "content": [{"type": "input_text", "text": "strong request"}],
                                },
                            },
                            ensure_ascii=False,
                        ),
                        json.dumps(
                            {
                                "timestamp": "2026-04-25T06:08:45Z",
                                "type": "response_item",
                                "payload": {
                                    "type": "message",
                                    "role": "assistant",
                                    "content": [{"type": "output_text", "text": "strong assistant"}],
                                },
                            },
                            ensure_ascii=False,
                        ),
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            inspect = run_cli(
                project_root,
                "inspect",
                "--tool",
                "codex",
                "--json",
                "--limit",
                "2",
                extra_env={"AISS_CODEX_HOME": str(codex_home)},
            )
            self.assertEqual(inspect.returncode, 0, inspect.stderr)
            payload = json.loads(inspect.stdout)
            self.assertEqual(payload["codex"][0]["session_id"], "strong")
            self.assertEqual(payload["codex"][0]["goal_candidate"], "strong request")
            self.assertIn("all_excerpts", payload["codex"][0])
            self.assertGreaterEqual(len(payload["codex"][0]["all_excerpts"]), len(payload["codex"][0]["excerpts"]))
            self.assertIn("selected", payload["codex"][0]["all_excerpts"][0])
            self.assertIn("selected_index", payload["codex"][0]["all_excerpts"][0])
            self.assertIn("all_excerpt_index", payload["codex"][0]["excerpts"][0])

    def test_codex_inspect_json_includes_compare_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_root = Path(tmp) / "repo"
            project_root.mkdir()
            codex_home = Path(tmp) / "codex-home"
            sessions_dir = codex_home / "sessions" / "2026" / "04" / "25"
            sessions_dir.mkdir(parents=True)
            (codex_home / "session_index.jsonl").write_text(
                json.dumps(
                    {
                        "id": "compare-json-session",
                        "thread_name": "Compare json metadata",
                        "updated_at": "2026-04-25T06:00:00Z",
                    },
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )
            records = [
                {
                    "timestamp": "2026-04-25T05:50:00Z",
                    "type": "session_meta",
                    "payload": {"id": "compare-json-session", "cwd": str(project_root)},
                }
            ]
            for index in range(14):
                role = "user" if index == 3 else "assistant"
                block_type = "input_text" if role == "user" else "output_text"
                records.append(
                    {
                        "timestamp": transcript_timestamp(start_minute=51, offset=index),
                        "type": "response_item",
                        "payload": {
                            "type": "message",
                            "role": role,
                            "content": [{"type": block_type, "text": f"message {index}"}],
                        },
                    }
                )
            transcript = sessions_dir / "compare-json.jsonl"
            transcript.write_text("\n".join(json.dumps(record, ensure_ascii=False) for record in records) + "\n", encoding="utf-8")

            inspect = run_cli(
                project_root,
                "inspect",
                "--tool",
                "codex",
                "--json",
                "--limit",
                "1",
                extra_env={"AISS_CODEX_HOME": str(codex_home)},
            )
            self.assertEqual(inspect.returncode, 0, inspect.stderr)
            payload = json.loads(inspect.stdout)
            all_excerpts = payload["codex"][0]["all_excerpts"]
            selected_entries = [excerpt for excerpt in all_excerpts if excerpt["selected"]]
            trimmed_entries = [excerpt for excerpt in all_excerpts if not excerpt["selected"]]
            excerpts = payload["codex"][0]["excerpts"]

            self.assertTrue(selected_entries)
            self.assertTrue(trimmed_entries)
            self.assertEqual([excerpt["selected_index"] for excerpt in selected_entries], list(range(1, len(selected_entries) + 1)))
            self.assertTrue(all(excerpt["selected_index"] is None for excerpt in trimmed_entries))
            self.assertEqual([excerpt["selected_index"] for excerpt in excerpts], list(range(1, len(excerpts) + 1)))
            self.assertEqual(
                [excerpt["all_excerpt_index"] for excerpt in excerpts],
                [entry["selected_index"] and index for index, entry in enumerate(all_excerpts, start=1) if entry["selected"]],
            )

    def test_codex_inspect_all_excerpts_and_full_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_root = Path(tmp) / "repo"
            project_root.mkdir()
            codex_home = Path(tmp) / "codex-home"
            sessions_dir = codex_home / "sessions" / "2026" / "04" / "25"
            sessions_dir.mkdir(parents=True)
            (codex_home / "session_index.jsonl").write_text(
                json.dumps(
                    {
                        "id": "session-heavy",
                        "thread_name": "Verbose session",
                        "updated_at": "2026-04-25T06:00:00Z",
                    },
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )
            records = [
                {
                    "timestamp": "2026-04-25T05:50:00Z",
                    "type": "session_meta",
                    "payload": {"id": "session-heavy", "cwd": str(project_root)},
                }
            ]
            for index in range(15):
                role = "user" if index == 2 else "assistant"
                block_type = "input_text" if role == "user" else "output_text"
                text = f"very long message {index} " + ("x" * 320)
                records.append(
                    {
                        "timestamp": transcript_timestamp(start_minute=51, offset=index),
                        "type": "response_item",
                        "payload": {
                            "type": "message",
                            "role": role,
                            "content": [{"type": block_type, "text": text}],
                        },
                    }
                )
            transcript = sessions_dir / "verbose.jsonl"
            transcript.write_text("\n".join(json.dumps(record, ensure_ascii=False) for record in records) + "\n", encoding="utf-8")

            inspect = run_cli(
                project_root,
                "inspect",
                "--tool",
                "codex",
                "--limit",
                "1",
                "--all-excerpts",
                "--full",
                extra_env={"AISS_CODEX_HOME": str(codex_home)},
            )
            self.assertEqual(inspect.returncode, 0, inspect.stderr)
            self.assertIn("showing: all excerpts", inspect.stdout)
            self.assertIn("very long message 14", inspect.stdout)
            self.assertGreater(inspect.stdout.count("assistant:"), 10)

    def test_codex_inspect_compare_view_marks_selected_and_trimmed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_root = Path(tmp) / "repo"
            project_root.mkdir()
            codex_home = Path(tmp) / "codex-home"
            sessions_dir = codex_home / "sessions" / "2026" / "04" / "25"
            sessions_dir.mkdir(parents=True)
            (codex_home / "session_index.jsonl").write_text(
                json.dumps(
                    {
                        "id": "compare-session",
                        "thread_name": "Compare window selection",
                        "updated_at": "2026-04-25T06:00:00Z",
                    },
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )
            records = [
                {
                    "timestamp": "2026-04-25T05:50:00Z",
                    "type": "session_meta",
                    "payload": {"id": "compare-session", "cwd": str(project_root)},
                }
            ]
            for index in range(14):
                role = "user" if index == 3 else "assistant"
                block_type = "input_text" if role == "user" else "output_text"
                records.append(
                    {
                        "timestamp": transcript_timestamp(start_minute=51, offset=index),
                        "type": "response_item",
                        "payload": {
                            "type": "message",
                            "role": role,
                            "content": [{"type": block_type, "text": f"message {index}"}],
                        },
                    }
                )
            transcript = sessions_dir / "compare.jsonl"
            transcript.write_text("\n".join(json.dumps(record, ensure_ascii=False) for record in records) + "\n", encoding="utf-8")

            inspect = run_cli(
                project_root,
                "inspect",
                "--tool",
                "codex",
                "--limit",
                "1",
                "--compare",
                extra_env={"AISS_CODEX_HOME": str(codex_home)},
            )
            self.assertEqual(inspect.returncode, 0, inspect.stderr)
            self.assertIn("showing: compare view (selected excerpts vs all excerpts)", inspect.stdout)
            self.assertIn("selected excerpts:", inspect.stdout)
            self.assertIn("all excerpts:", inspect.stdout)
            self.assertIn("[selected]", inspect.stdout)
            self.assertIn("[trimmed ]", inspect.stdout)

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

    def test_claude_inspect_shows_goal_candidate(self) -> None:
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
                                    "content": [{"type": "text", "text": "请继续实现 inspect 预览。"}],
                                },
                                "timestamp": "2026-04-25T08:00:00Z",
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
                                    "content": [{"type": "text", "text": "我会把 score、goal、excerpt 都展示出来。"}],
                                },
                                "timestamp": "2026-04-25T08:00:05Z",
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

            inspect = run_cli(
                project_root,
                "inspect",
                "--tool",
                "claude",
                "--json",
                extra_env={"AISS_CLAUDE_HOME": str(claude_home)},
            )
            self.assertEqual(inspect.returncode, 0, inspect.stderr)
            payload = json.loads(inspect.stdout)
            self.assertEqual(payload["claude"][0]["goal_candidate"], "请继续实现 inspect 预览。")
            self.assertIn("score", payload["claude"][0])
            self.assertEqual(payload["claude"][0]["excerpts"][0]["role"], "user")


if __name__ == "__main__":
    unittest.main()
