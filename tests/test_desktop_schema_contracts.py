from __future__ import annotations

import json
import unittest
from pathlib import Path

from tests.schema_utils import assert_matches_schema, load_schema


class DesktopSchemaContractTest(unittest.TestCase):
    def setUp(self) -> None:
        self.manifest_schema = load_schema("manifest.schema.json")
        self.inspect_schema = load_schema("inspect-output.schema.json")
        self.latest_pointer_schema = load_schema("latest-pointer.schema.json")
        self.ui_bundle_schema = load_schema("ui-bundle.schema.json")
        self.session_catalog_schema = load_schema("session-catalog.schema.json")
        self.session_detail_schema = load_schema("session-detail.schema.json")
        self.project_catalog_schema = load_schema("project-catalog.schema.json")
        self.desktop_ui_bundle_schema = load_schema("desktop-ui-bundle.schema.json")
        self.public_examples_dir = (
            Path(__file__).resolve().parents[1] / "docs" / "examples" / "public-sync-state"
        )
        self.desktop_examples_dir = (
            Path(__file__).resolve().parents[1] / "docs" / "examples" / "desktop"
        )

    def _load_public_json(self, name: str) -> dict[str, object]:
        return json.loads((self.public_examples_dir / name).read_text(encoding="utf-8"))

    def _load_desktop_json(self, name: str) -> dict[str, object]:
        return json.loads((self.desktop_examples_dir / name).read_text(encoding="utf-8"))

    def _build_session_catalog_payload(self) -> dict[str, object]:
        clean_bundle = self._load_public_json("sample-ui-bundle.json")
        dirty_bundle = self._load_public_json("sample-ui-bundle-dirty.json")
        conflict_bundle = self._load_public_json("sample-ui-bundle-conflict.json")

        clean_context = clean_bundle["manifest"]["source"]["contexts"][0]
        dirty_context = dirty_bundle["manifest"]["source"]["contexts"][0]
        conflict_context = conflict_bundle["manifest"]["source"]["contexts"][0]

        return {
            "schema_version": "0.1.0",
            "generated_at": "2026-04-29T10:00:00Z",
            "sessions": [
                {
                    "session_key": "codex:transcript:session-sample-001",
                    "tool": clean_context["tool"],
                    "source_kind": clean_context["source_kind"],
                    "native_session_id": clean_context["session_id"],
                    "title": clean_context["title"],
                    "native_title": clean_context["title"],
                    "project_id": clean_bundle["manifest"]["project"]["id"],
                    "project_label": clean_bundle["manifest"]["project"]["id"],
                    "updated_at": clean_context["updated_at"],
                    "transcript_path": clean_context["transcript_path"],
                    "cwd": clean_bundle["inspect"]["codex"][0]["cwd"],
                    "score": clean_context["score"],
                    "score_reasons": clean_context["score_reasons"],
                    "goal_candidate": clean_context["goal_candidate"],
                    "excerpt_count": clean_context["excerpt_count"],
                    "total_excerpt_count": clean_context["total_excerpt_count"],
                    "total_user_count": clean_context["total_user_count"],
                    "total_assistant_count": clean_context["total_assistant_count"],
                    "latest_state": "ready",
                    "latest_snapshot_id": clean_bundle["manifest"]["snapshot_id"],
                    "has_handoff": True,
                    "has_patch": False,
                    "patch_replay_state": clean_bundle["patch_replay"]["state"],
                    "status_flags": []
                },
                {
                    "session_key": "claude:transcript:session-sample-claude-002",
                    "tool": dirty_context["tool"],
                    "source_kind": dirty_context["source_kind"],
                    "native_session_id": dirty_context["session_id"],
                    "title": dirty_context["title"],
                    "native_title": dirty_context["title"],
                    "project_id": dirty_bundle["manifest"]["project"]["id"],
                    "project_label": dirty_bundle["manifest"]["project"]["id"],
                    "updated_at": dirty_context["updated_at"],
                    "transcript_path": dirty_context["transcript_path"],
                    "cwd": dirty_bundle["inspect"]["claude"][0]["cwd"],
                    "score": dirty_context["score"],
                    "score_reasons": dirty_context["score_reasons"],
                    "goal_candidate": dirty_context["goal_candidate"],
                    "excerpt_count": dirty_context["excerpt_count"],
                    "total_excerpt_count": dirty_context["total_excerpt_count"],
                    "total_user_count": dirty_context["total_user_count"],
                    "total_assistant_count": dirty_context["total_assistant_count"],
                    "latest_state": "ready",
                    "latest_snapshot_id": dirty_bundle["manifest"]["snapshot_id"],
                    "has_handoff": True,
                    "has_patch": True,
                    "patch_replay_state": dirty_bundle["patch_replay"]["state"],
                    "status_flags": ["dirty", "patch", "warning"]
                },
                {
                    "session_key": "codex:transcript:session-sample-conflict-001",
                    "tool": conflict_context["tool"],
                    "source_kind": conflict_context["source_kind"],
                    "native_session_id": conflict_context["session_id"],
                    "title": conflict_context["title"],
                    "native_title": conflict_context["title"],
                    "project_id": conflict_bundle["manifest"]["project"]["id"],
                    "project_label": conflict_bundle["manifest"]["project"]["id"],
                    "updated_at": conflict_context["updated_at"],
                    "transcript_path": conflict_context["transcript_path"],
                    "cwd": conflict_bundle["inspect"]["codex"][0]["cwd"],
                    "score": conflict_context["score"],
                    "score_reasons": conflict_context["score_reasons"],
                    "goal_candidate": conflict_context["goal_candidate"],
                    "excerpt_count": conflict_context["excerpt_count"],
                    "total_excerpt_count": conflict_context["total_excerpt_count"],
                    "total_user_count": conflict_context["total_user_count"],
                    "total_assistant_count": conflict_context["total_assistant_count"],
                    "latest_state": "conflict",
                    "latest_snapshot_id": None,
                    "has_handoff": True,
                    "has_patch": True,
                    "patch_replay_state": conflict_bundle["patch_replay"]["state"],
                    "status_flags": ["conflict", "patch"]
                }
            ],
            "projects": [
                {
                    "project_id": "sample-project",
                    "display_name": "sample-project",
                    "session_count": 3,
                    "tool_counts": {"codex": 2, "claude": 1},
                    "latest_updated_at": "2026-04-25T08:16:45Z",
                    "roots": ["${PROJECT_ROOT}"]
                }
            ],
            "summary": {
                "total_sessions": 3,
                "total_projects": 1,
                "tool_counts": {"codex": 2, "claude": 1},
                "status_counts": {"dirty": 1, "patch": 2, "conflict": 1, "warning": 1}
            }
        }

    def _build_session_detail_payload(self) -> dict[str, object]:
        dirty_bundle = self._load_public_json("sample-ui-bundle-dirty.json")
        dirty_context = dirty_bundle["manifest"]["source"]["contexts"][0]
        dirty_inspect = dirty_bundle["inspect"]["claude"][0]

        return {
            "schema_version": "0.1.0",
            "generated_at": "2026-04-29T10:00:00Z",
            "session": {
                "session_key": "claude:transcript:session-sample-claude-002",
                "tool": dirty_context["tool"],
                "source_kind": dirty_context["source_kind"],
                "native_session_id": dirty_context["session_id"],
                "title": dirty_context["title"],
                "native_title": dirty_context["title"],
                "project_id": dirty_bundle["manifest"]["project"]["id"],
                "project_label": dirty_bundle["manifest"]["project"]["id"],
                "updated_at": dirty_context["updated_at"],
                "transcript_path": dirty_context["transcript_path"],
                "cwd": dirty_inspect["cwd"],
                "goal_candidate": dirty_context["goal_candidate"],
                "score": dirty_context["score"],
                "score_reasons": dirty_context["score_reasons"],
                "excerpt_count": dirty_context["excerpt_count"],
                "total_excerpt_count": dirty_context["total_excerpt_count"],
                "total_user_count": dirty_context["total_user_count"],
                "total_assistant_count": dirty_context["total_assistant_count"],
                "raw_message_count": dirty_context["total_excerpt_count"],
                "selected_excerpt_count": len(dirty_inspect["excerpts"]),
                "all_excerpt_count": len(dirty_inspect["all_excerpts"]),
                "device_id": dirty_bundle["manifest"]["source"]["device_id"],
                "provider_profile": dirty_bundle["manifest"]["source"]["provider_profile"],
                "latest_state": "ready",
                "latest_snapshot_id": dirty_bundle["manifest"]["snapshot_id"],
                "latest_candidates": [dirty_bundle["manifest"]["snapshot_id"]],
                "has_handoff": True,
                "has_patch": True,
                "patch_replay_state": dirty_bundle["patch_replay"]["state"],
                "status_flags": ["dirty", "patch", "warning"]
            },
            "manifest": dirty_bundle["manifest"],
            "inspect": {"claude": dirty_bundle["inspect"]["claude"]},
            "handoff": dirty_bundle["handoff"],
            "patch_replay": dirty_bundle["patch_replay"],
            "provenance": {
                "session": "derived",
                "manifest": "source-of-truth",
                "inspect": "source-of-truth",
                "handoff": "source-of-truth",
                "patch_replay": "source-of-truth"
            }
        }

    def _build_project_catalog_payload(self) -> dict[str, object]:
        clean_bundle = self._load_public_json("sample-ui-bundle.json")
        dirty_bundle = self._load_public_json("sample-ui-bundle-dirty.json")
        conflict_bundle = self._load_public_json("sample-ui-bundle-conflict.json")

        return {
            "schema_version": "0.1.0",
            "generated_at": "2026-04-29T10:00:00Z",
            "projects": [
                {
                    "project_id": "sample-project",
                    "display_name": "sample-project",
                    "roots": ["${PROJECT_ROOT}"],
                    "git_remote": clean_bundle["manifest"]["project"]["git_remote"],
                    "branch": clean_bundle["manifest"]["project"]["branch"],
                    "head": clean_bundle["manifest"]["project"]["head"],
                    "session_count": 3,
                    "active_tools": ["codex", "claude"],
                    "latest_snapshot_ids": {
                        "codex": clean_bundle["manifest"]["snapshot_id"],
                        "claude": dirty_bundle["manifest"]["snapshot_id"]
                    },
                    "latest_conflicts": {
                        "codex": conflict_bundle["latest"]["candidates"],
                        "claude": []
                    },
                    "sessions": [
                        {
                            "session_key": "codex:transcript:session-sample-001",
                            "tool": "codex",
                            "title": clean_bundle["manifest"]["source"]["contexts"][0]["title"],
                            "updated_at": clean_bundle["manifest"]["source"]["contexts"][0]["updated_at"],
                            "goal_candidate": clean_bundle["manifest"]["source"]["contexts"][0]["goal_candidate"],
                            "score": clean_bundle["manifest"]["source"]["contexts"][0]["score"],
                            "status_flags": []
                        },
                        {
                            "session_key": "claude:transcript:session-sample-claude-002",
                            "tool": "claude",
                            "title": dirty_bundle["manifest"]["source"]["contexts"][0]["title"],
                            "updated_at": dirty_bundle["manifest"]["source"]["contexts"][0]["updated_at"],
                            "goal_candidate": dirty_bundle["manifest"]["source"]["contexts"][0]["goal_candidate"],
                            "score": dirty_bundle["manifest"]["source"]["contexts"][0]["score"],
                            "status_flags": ["dirty", "patch", "warning"]
                        },
                        {
                            "session_key": "codex:transcript:session-sample-conflict-001",
                            "tool": "codex",
                            "title": conflict_bundle["manifest"]["source"]["contexts"][0]["title"],
                            "updated_at": conflict_bundle["manifest"]["source"]["contexts"][0]["updated_at"],
                            "goal_candidate": conflict_bundle["manifest"]["source"]["contexts"][0]["goal_candidate"],
                            "score": conflict_bundle["manifest"]["source"]["contexts"][0]["score"],
                            "status_flags": ["conflict", "patch"]
                        }
                    ],
                    "recommended_session_key": "codex:transcript:session-sample-conflict-001"
                }
            ],
            "summary": {
                "total_projects": 1,
                "total_sessions": 3,
                "tool_counts": {"codex": 2, "claude": 1},
                "latest_conflict_count": 1
            },
            "selected_project": {
                "project_id": "sample-project",
                "display_name": "sample-project",
                "roots": ["${PROJECT_ROOT}"],
                "git_remote": clean_bundle["manifest"]["project"]["git_remote"],
                "branch": clean_bundle["manifest"]["project"]["branch"],
                "head": clean_bundle["manifest"]["project"]["head"],
                "session_count": 3,
                "active_tools": ["codex", "claude"],
                "latest_snapshot_ids": {
                    "codex": clean_bundle["manifest"]["snapshot_id"],
                    "claude": dirty_bundle["manifest"]["snapshot_id"]
                },
                "latest_conflicts": {
                    "codex": conflict_bundle["latest"]["candidates"],
                    "claude": []
                },
                "sessions": [
                    {
                        "session_key": "codex:transcript:session-sample-001",
                        "tool": "codex",
                        "title": clean_bundle["manifest"]["source"]["contexts"][0]["title"],
                        "updated_at": clean_bundle["manifest"]["source"]["contexts"][0]["updated_at"],
                        "goal_candidate": clean_bundle["manifest"]["source"]["contexts"][0]["goal_candidate"],
                        "score": clean_bundle["manifest"]["source"]["contexts"][0]["score"],
                        "status_flags": []
                    },
                    {
                        "session_key": "claude:transcript:session-sample-claude-002",
                        "tool": "claude",
                        "title": dirty_bundle["manifest"]["source"]["contexts"][0]["title"],
                        "updated_at": dirty_bundle["manifest"]["source"]["contexts"][0]["updated_at"],
                        "goal_candidate": dirty_bundle["manifest"]["source"]["contexts"][0]["goal_candidate"],
                        "score": dirty_bundle["manifest"]["source"]["contexts"][0]["score"],
                        "status_flags": ["dirty", "patch", "warning"]
                    },
                    {
                        "session_key": "codex:transcript:session-sample-conflict-001",
                        "tool": "codex",
                        "title": conflict_bundle["manifest"]["source"]["contexts"][0]["title"],
                        "updated_at": conflict_bundle["manifest"]["source"]["contexts"][0]["updated_at"],
                        "goal_candidate": conflict_bundle["manifest"]["source"]["contexts"][0]["goal_candidate"],
                        "score": conflict_bundle["manifest"]["source"]["contexts"][0]["score"],
                        "status_flags": ["conflict", "patch"]
                    }
                ],
                "recommended_session_key": "codex:transcript:session-sample-conflict-001"
            }
        }

    def _build_desktop_ui_bundle_payload(self) -> dict[str, object]:
        session_catalog = self._build_session_catalog_payload()
        project_catalog = self._build_project_catalog_payload()
        session_detail = self._build_session_detail_payload()
        return {
            "schema_version": "0.1.0",
            "bundle_id": "desktop-sample-bundle",
            "generated_at": "2026-04-29T10:00:00Z",
            "session_catalog": session_catalog,
            "project_catalog": project_catalog,
            "selected_session_detail": session_detail,
            "view_state": {
                "active_view": "session-detail",
                "selected_session_key": session_detail["session"]["session_key"],
                "selected_project_id": session_detail["session"]["project_id"],
                "data_mode": "fixture",
                "filters": {
                    "tool": "all",
                    "project_id": session_detail["session"]["project_id"],
                    "status": "dirty",
                    "q": "",
                    "sort": "updated_at",
                    "order": "desc"
                }
            }
        }

    def test_session_catalog_payload_matches_schema(self) -> None:
        payload = self._build_session_catalog_payload()
        assert_matches_schema(payload, self.session_catalog_schema)
        self.assertEqual(payload["summary"]["total_sessions"], len(payload["sessions"]))
        self.assertEqual(payload["summary"]["total_projects"], len(payload["projects"]))
        self.assertEqual(payload["projects"][0]["session_count"], len(payload["sessions"]))
        self.assertIn("conflict", payload["sessions"][2]["status_flags"])
        self.assertEqual(payload["sessions"][2]["latest_state"], "conflict")
        self.assertIsNone(payload["sessions"][2]["latest_snapshot_id"])

    def test_session_detail_payload_matches_schema_and_nested_contracts(self) -> None:
        payload = self._build_session_detail_payload()
        assert_matches_schema(payload, self.session_detail_schema)
        assert_matches_schema(payload["manifest"], self.manifest_schema)
        assert_matches_schema(payload["inspect"], self.inspect_schema)
        self.assertEqual(payload["session"]["selected_excerpt_count"], len(payload["inspect"]["claude"][0]["excerpts"]))
        self.assertEqual(payload["session"]["all_excerpt_count"], len(payload["inspect"]["claude"][0]["all_excerpts"]))
        self.assertEqual(payload["session"]["goal_candidate"], payload["manifest"]["source"]["contexts"][0]["goal_candidate"])
        self.assertEqual(payload["handoff"]["current_goal"], payload["manifest"]["source"]["contexts"][0]["goal_candidate"])
        self.assertEqual(payload["patch_replay"]["state"], "blocked")
        self.assertEqual(payload["provenance"]["session"], "derived")
        self.assertEqual(payload["provenance"]["manifest"], "source-of-truth")

    def test_project_catalog_payload_matches_schema(self) -> None:
        payload = self._build_project_catalog_payload()
        assert_matches_schema(payload, self.project_catalog_schema)
        self.assertEqual(payload["summary"]["total_projects"], len(payload["projects"]))
        self.assertEqual(payload["summary"]["total_sessions"], payload["projects"][0]["session_count"])
        self.assertEqual(payload["selected_project"]["recommended_session_key"], "codex:transcript:session-sample-conflict-001")
        self.assertEqual(
            payload["projects"][0]["latest_conflicts"]["codex"],
            [
                "20260425T080000Z-sample-macbook-codex",
                "20260425T081500Z-sample-windows-codex"
            ],
        )

    def test_desktop_ui_bundle_matches_schema_and_nested_contracts(self) -> None:
        payload = self._build_desktop_ui_bundle_payload()
        assert_matches_schema(payload, self.desktop_ui_bundle_schema)
        assert_matches_schema(payload["session_catalog"], self.session_catalog_schema)
        assert_matches_schema(payload["project_catalog"], self.project_catalog_schema)
        assert_matches_schema(payload["selected_session_detail"], self.session_detail_schema)
        self.assertEqual(
            payload["view_state"]["selected_session_key"],
            payload["selected_session_detail"]["session"]["session_key"],
        )
        self.assertEqual(
            payload["view_state"]["selected_project_id"],
            payload["selected_session_detail"]["session"]["project_id"],
        )
        self.assertEqual(payload["view_state"]["active_view"], "session-detail")

    def test_existing_public_ui_bundle_still_matches_current_schema(self) -> None:
        payload = self._load_public_json("sample-ui-bundle.json")
        assert_matches_schema(payload, self.ui_bundle_schema)
        assert_matches_schema(payload["latest"], self.latest_pointer_schema)
        assert_matches_schema(payload["manifest"], self.manifest_schema)
        assert_matches_schema(payload["inspect"], self.inspect_schema)

    def test_desktop_session_catalog_fixture_matches_schema(self) -> None:
        payload = self._load_desktop_json("sample-session-catalog.json")
        assert_matches_schema(payload, self.session_catalog_schema)
        self.assertEqual(payload["summary"]["total_sessions"], len(payload["sessions"]))
        self.assertEqual(payload["summary"]["total_projects"], len(payload["projects"]))
        self.assertEqual(payload["projects"][0]["session_count"], len(payload["sessions"]))

    def test_desktop_session_detail_codex_fixture_matches_schema_and_nested_contracts(self) -> None:
        payload = self._load_desktop_json("sample-session-detail-codex.json")
        assert_matches_schema(payload, self.session_detail_schema)
        assert_matches_schema(payload["manifest"], self.manifest_schema)
        assert_matches_schema(payload["inspect"], self.inspect_schema)
        self.assertEqual(payload["session"]["tool"], "codex")
        self.assertEqual(payload["patch_replay"]["state"], "none")

    def test_desktop_session_detail_claude_fixture_matches_schema_and_nested_contracts(self) -> None:
        payload = self._load_desktop_json("sample-session-detail-claude.json")
        assert_matches_schema(payload, self.session_detail_schema)
        assert_matches_schema(payload["manifest"], self.manifest_schema)
        assert_matches_schema(payload["inspect"], self.inspect_schema)
        self.assertEqual(payload["session"]["tool"], "claude")
        self.assertEqual(payload["patch_replay"]["state"], "blocked")
        self.assertIn("dirty", payload["session"]["status_flags"])

    def test_desktop_session_detail_conflict_fixture_matches_schema_and_nested_contracts(self) -> None:
        payload = self._load_desktop_json("sample-session-detail-conflict.json")
        assert_matches_schema(payload, self.session_detail_schema)
        assert_matches_schema(payload["manifest"], self.manifest_schema)
        assert_matches_schema(payload["inspect"], self.inspect_schema)
        self.assertEqual(payload["session"]["latest_state"], "conflict")
        self.assertEqual(
            payload["session"]["latest_candidates"],
            [
                "20260425T080000Z-sample-macbook-codex",
                "20260425T081500Z-sample-windows-codex",
            ],
        )

    def test_desktop_project_catalog_fixture_matches_schema(self) -> None:
        payload = self._load_desktop_json("sample-project-catalog.json")
        assert_matches_schema(payload, self.project_catalog_schema)
        self.assertEqual(payload["summary"]["total_projects"], len(payload["projects"]))
        self.assertEqual(payload["summary"]["total_sessions"], payload["projects"][0]["session_count"])
        self.assertEqual(payload["summary"]["latest_conflict_count"], 1)

    def test_desktop_ui_bundle_fixture_matches_schema_and_nested_contracts(self) -> None:
        payload = self._load_desktop_json("sample-desktop-ui-bundle.json")
        assert_matches_schema(payload, self.desktop_ui_bundle_schema)
        assert_matches_schema(payload["session_catalog"], self.session_catalog_schema)
        assert_matches_schema(payload["project_catalog"], self.project_catalog_schema)
        assert_matches_schema(payload["selected_session_detail"], self.session_detail_schema)
        assert_matches_schema(payload["selected_session_detail"]["manifest"], self.manifest_schema)
        assert_matches_schema(payload["selected_session_detail"]["inspect"], self.inspect_schema)
        self.assertEqual(payload["view_state"]["active_view"], "session-detail")
        self.assertEqual(
            payload["view_state"]["selected_session_key"],
            payload["selected_session_detail"]["session"]["session_key"],
        )
        self.assertEqual(
            payload["view_state"]["selected_project_id"],
            payload["selected_session_detail"]["session"]["project_id"],
        )


if __name__ == "__main__":
    unittest.main()
