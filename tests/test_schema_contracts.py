from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tests.cli_test_utils import run_cli, transcript_timestamp
from tests.schema_utils import assert_matches_schema, load_schema


class SchemaContractTest(unittest.TestCase):
    def setUp(self) -> None:
        self.manifest_schema = load_schema("manifest.schema.json")
        self.inspect_schema = load_schema("inspect-output.schema.json")
        self.latest_pointer_schema = load_schema("latest-pointer.schema.json")
        self.ui_bundle_schema = load_schema("ui-bundle.schema.json")
        self.public_examples_dir = (
            Path(__file__).resolve().parents[1] / "docs" / "examples" / "public-sync-state"
        )

    def _assert_compare_indexes_consistent(self, payload: dict[str, list[dict[str, object]]]) -> None:
        for contexts in payload.values():
            for context in contexts:
                all_excerpts = context["all_excerpts"]
                excerpts = context["excerpts"]
                selected_entries = [excerpt for excerpt in all_excerpts if excerpt["selected"]]
                trimmed_entries = [excerpt for excerpt in all_excerpts if not excerpt["selected"]]

                self.assertEqual(
                    [excerpt["selected_index"] for excerpt in selected_entries],
                    list(range(1, len(selected_entries) + 1)),
                )
                self.assertTrue(all(excerpt["selected_index"] is None for excerpt in trimmed_entries))
                self.assertEqual([excerpt["selected_index"] for excerpt in excerpts], list(range(1, len(excerpts) + 1)))
                self.assertEqual(
                    [excerpt["all_excerpt_index"] for excerpt in excerpts],
                    [index for index, entry in enumerate(all_excerpts, start=1) if entry["selected"]],
                )

    def test_codex_export_outputs_match_manifest_and_latest_schema(self) -> None:
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
                                "payload": {"id": "session-123", "cwd": str(project_root)},
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
                                    "content": [{"type": "input_text", "text": "continue transcript extraction"}],
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
                                    "content": [{"type": "output_text", "text": "working on export context"}],
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
            assert_matches_schema(latest, self.latest_pointer_schema)
            assert_matches_schema(manifest, self.manifest_schema)

    def test_claude_export_outputs_match_manifest_and_latest_schema(self) -> None:
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
                                    "content": [{"type": "text", "text": "我会优先读取项目 transcript。"}],
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
            assert_matches_schema(latest, self.latest_pointer_schema)
            assert_matches_schema(manifest, self.manifest_schema)

    def test_codex_inspect_json_matches_schema_and_compare_indexes_are_consistent(self) -> None:
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
            assert_matches_schema(payload, self.inspect_schema)
            self._assert_compare_indexes_consistent(payload)
            self.assertTrue(any(not excerpt["selected"] for excerpt in payload["codex"][0]["all_excerpts"]))

    def test_claude_inspect_json_matches_schema(self) -> None:
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
            assert_matches_schema(payload, self.inspect_schema)
            self.assertEqual(payload["claude"][0]["excerpts"][0]["role"], "user")

    def test_latest_pointer_conflict_shape_matches_schema(self) -> None:
        payload = {
            "candidates": [
                "20260423T151230Z-macbook-codex",
                "20260423T152010Z-windows-codex",
            ],
            "requires_selection": True,
        }

        assert_matches_schema(payload, self.latest_pointer_schema)

    def test_public_manifest_fixture_matches_schema(self) -> None:
        payload = json.loads((self.public_examples_dir / "sample-manifest.json").read_text(encoding="utf-8"))
        assert_matches_schema(payload, self.manifest_schema)

    def test_public_inspect_fixture_matches_schema_and_compare_indexes_are_consistent(self) -> None:
        payload = json.loads((self.public_examples_dir / "sample-inspect-output.json").read_text(encoding="utf-8"))
        assert_matches_schema(payload, self.inspect_schema)
        self._assert_compare_indexes_consistent(payload)

    def test_public_latest_pointer_fixture_matches_schema(self) -> None:
        payload = json.loads((self.public_examples_dir / "sample-latest-pointer.json").read_text(encoding="utf-8"))
        assert_matches_schema(payload, self.latest_pointer_schema)

    def test_public_latest_conflict_fixture_matches_schema(self) -> None:
        payload = json.loads((self.public_examples_dir / "sample-latest-conflict.json").read_text(encoding="utf-8"))
        assert_matches_schema(payload, self.latest_pointer_schema)

    def test_public_dirty_manifest_fixture_matches_schema(self) -> None:
        payload = json.loads((self.public_examples_dir / "sample-manifest-dirty.json").read_text(encoding="utf-8"))
        assert_matches_schema(payload, self.manifest_schema)

        self.assertTrue(payload["project"]["dirty"])
        self.assertTrue(payload["artifacts"]["patch"])
        self.assertTrue(payload["redaction"]["warnings"])
        self.assertGreater(len(payload["source"]["contexts"]), 1)

    def test_public_dirty_inspect_fixture_matches_schema_and_compare_indexes_are_consistent(self) -> None:
        payload = json.loads((self.public_examples_dir / "sample-inspect-output-dirty.json").read_text(encoding="utf-8"))
        assert_matches_schema(payload, self.inspect_schema)
        self._assert_compare_indexes_consistent(payload)

        self.assertTrue(any(not excerpt["selected"] for excerpt in payload["claude"][0]["all_excerpts"]))

    def test_public_ui_bundle_fixture_matches_schema_and_embedded_contracts(self) -> None:
        payload = json.loads((self.public_examples_dir / "sample-ui-bundle.json").read_text(encoding="utf-8"))
        assert_matches_schema(payload, self.ui_bundle_schema)
        assert_matches_schema(payload["latest"], self.latest_pointer_schema)
        assert_matches_schema(payload["manifest"], self.manifest_schema)
        assert_matches_schema(payload["inspect"], self.inspect_schema)
        self._assert_compare_indexes_consistent(payload["inspect"])

        entry = payload["entry"]
        manifest = payload["manifest"]
        latest = payload["latest"]
        inspect = payload["inspect"]
        handoff = payload["handoff"]
        manifest_context = manifest["source"]["contexts"][0]
        active_context = inspect[entry["active_tool"]][0]

        self.assertEqual(entry["snapshot_id"], latest["snapshot_id"])
        self.assertEqual(entry["snapshot_id"], manifest["snapshot_id"])
        self.assertEqual(latest["manifest"], f"manifests/{manifest['snapshot_id']}.json")
        self.assertEqual(entry["project_id"], manifest["project"]["id"])
        self.assertEqual(entry["active_tool"], manifest["source"]["tool"])
        self.assertEqual(set(entry["available_tools"]), set(inspect))
        self.assertIn(entry["active_tool"], entry["available_tools"])
        self.assertEqual(entry["handoff_path"], manifest["artifacts"]["handoff"])
        self.assertEqual(handoff["path"], manifest["artifacts"]["handoff"])
        self.assertEqual(handoff["current_goal"], manifest_context["goal_candidate"])
        self.assertEqual(active_context["session_id"], manifest_context["session_id"])
        self.assertEqual(active_context["title"], manifest_context["title"])
        self.assertEqual(active_context["score"], manifest_context["score"])
        self.assertEqual(active_context["goal_candidate"], manifest_context["goal_candidate"])
        self.assertIn(handoff["title"], handoff["markdown"])
        self.assertIn(handoff["current_goal"], handoff["markdown"])


if __name__ == "__main__":
    unittest.main()
