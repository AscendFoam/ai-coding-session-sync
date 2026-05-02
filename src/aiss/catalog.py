"""Desktop-oriented catalog payload builders."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from .adapters import ExtractedContext, collect_claude_contexts, collect_codex_contexts
from .config import SyncConfig, load_sync_config
from .doctor import PatchReplayHealth, inspect_sync_health
from .patching import (
    PATCH_MODE_APPLY,
    PATCH_MODE_BRANCH,
    PATCH_MODE_THREE_WAY,
    default_patch_branch_name,
    inspect_patch,
)
from .project import default_project_id, git_info
from .schema import SCHEMA_VERSION, SYNC_DIR

SUPPORTED_DESKTOP_TOOLS = ("codex", "claude")


@dataclass(slots=True)
class SessionBinding:
    project_root: Path
    project_id: str
    project_label: str
    project_git: dict[str, object]
    tool: str
    context: ExtractedContext
    config: SyncConfig | None
    latest_payload: dict[str, object] | None
    latest_state: str
    latest_snapshot_id: str | None
    latest_candidates: list[str]
    manifest_path: Path | None
    manifest: dict[str, object] | None
    inspect_payload: dict[str, object]
    handoff: dict[str, object] | None
    patch_replay: dict[str, object]
    status_flags: list[str]

    @property
    def session_key(self) -> str:
        return make_session_key(self.context)


def build_session_catalog(
    project_roots: list[Path] | None = None,
    *,
    include_codex: bool = True,
    include_claude: bool = True,
) -> dict[str, object]:
    bindings = collect_catalog_sessions(
        project_roots or [],
        include_codex=include_codex,
        include_claude=include_claude,
    )
    return build_session_catalog_from_bindings(bindings)


def build_session_catalog_from_bindings(bindings: list[SessionBinding]) -> dict[str, object]:
    projects = _build_project_summaries(bindings)
    sessions = [_session_catalog_entry(binding) for binding in bindings]
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": _generated_at(),
        "sessions": sessions,
        "projects": projects,
        "summary": {
            "total_sessions": len(sessions),
            "total_projects": len(projects),
            "tool_counts": _tool_counts(bindings),
            "status_counts": _status_counts(bindings),
        },
    }


def build_session_detail(
    session_key: str,
    project_roots: list[Path] | None = None,
    *,
    include_codex: bool = True,
    include_claude: bool = True,
) -> dict[str, object]:
    bindings = collect_catalog_sessions(
        project_roots or [],
        include_codex=include_codex,
        include_claude=include_claude,
    )
    return build_session_detail_from_bindings(bindings, session_key)


def build_session_detail_from_bindings(bindings: list[SessionBinding], session_key: str) -> dict[str, object]:
    binding = find_session_binding(bindings, session_key)
    return build_session_detail_from_binding(binding)


def build_session_detail_from_binding(binding: SessionBinding) -> dict[str, object]:
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": _generated_at(),
        "session": _session_detail_entry(binding),
        "manifest": binding.manifest,
        "inspect": binding.inspect_payload,
        "handoff": binding.handoff,
        "patch_replay": binding.patch_replay,
        "provenance": {
            "session": "derived",
            "manifest": "source-of-truth" if binding.manifest is not None else "missing",
            "inspect": "source-of-truth",
            "handoff": "source-of-truth" if binding.handoff is not None else "missing",
            "patch_replay": "source-of-truth",
        },
    }


def find_session_binding(bindings: list[SessionBinding], session_key: str) -> SessionBinding:
    for binding in bindings:
        if binding.session_key == session_key:
            return binding
    raise KeyError(f"Unknown session key: {session_key}")


def build_project_catalog(
    project_roots: list[Path] | None = None,
    *,
    selected_project_id: str | None = None,
    include_codex: bool = True,
    include_claude: bool = True,
) -> dict[str, object]:
    bindings = collect_catalog_sessions(
        project_roots or [],
        include_codex=include_codex,
        include_claude=include_claude,
    )
    return build_project_catalog_from_bindings(bindings, selected_project_id=selected_project_id)


def build_project_catalog_from_bindings(
    bindings: list[SessionBinding],
    *,
    selected_project_id: str | None = None,
) -> dict[str, object]:
    grouped = _group_bindings_by_project(bindings)
    projects = [_project_catalog_entry(project_id, group) for project_id, group in grouped.items()]
    projects.sort(key=lambda item: item["display_name"])

    selected = None
    if projects:
        if selected_project_id:
            selected = next((item for item in projects if item["project_id"] == selected_project_id), None)
        if selected is None:
            selected = projects[0]

    latest_conflict_count = sum(
        1
        for item in projects
        if item["latest_conflicts"]["codex"] or item["latest_conflicts"]["claude"]
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": _generated_at(),
        "projects": projects,
        "summary": {
            "total_projects": len(projects),
            "total_sessions": len(bindings),
            "tool_counts": _tool_counts(bindings),
            "latest_conflict_count": latest_conflict_count,
        },
        "selected_project": selected,
    }


def collect_catalog_sessions(
    project_roots: list[Path],
    *,
    include_codex: bool = True,
    include_claude: bool = True,
) -> list[SessionBinding]:
    bindings: list[SessionBinding] = []
    for root in project_roots:
        project_root = root.expanduser().resolve(strict=False)
        if not project_root.exists():
            continue
        project_id = default_project_id(project_root)
        project_label = project_id
        project_git = git_info(project_root)
        config = _load_sync_config_if_present(project_root)
        tool_contexts = _collect_contexts(project_root, include_codex=include_codex, include_claude=include_claude)
        for tool, contexts in tool_contexts.items():
            latest_payload = _load_latest_pointer_if_exists(project_root / SYNC_DIR, tool)
            latest_state, latest_snapshot_id, latest_candidates = _summarize_latest_state(latest_payload)
            health = inspect_sync_health(project_root, config, tool=tool)
            for context in contexts:
                manifest_path, manifest = _match_manifest_for_context(project_root / SYNC_DIR, tool, context, latest_payload)
                inspect_payload = {tool: [_context_to_dict(context)]}
                handoff = _load_handoff_payload(project_root / SYNC_DIR, manifest)
                patch_replay = _patch_replay_payload(
                    project_root=project_root,
                    tool=tool,
                    health=health.patch_replay,
                    manifest=manifest,
                    manifest_matches_latest=latest_snapshot_id is not None
                    and manifest is not None
                    and manifest.get("snapshot_id") == latest_snapshot_id,
                )
                status_flags = _derive_status_flags(
                    latest_state=latest_state,
                    manifest=manifest,
                    patch_replay=patch_replay,
                )
                bindings.append(
                    SessionBinding(
                        project_root=project_root,
                        project_id=project_id,
                        project_label=project_label,
                        project_git=project_git,
                        tool=tool,
                        context=context,
                        config=config,
                        latest_payload=latest_payload,
                        latest_state=latest_state,
                        latest_snapshot_id=latest_snapshot_id,
                        latest_candidates=latest_candidates,
                        manifest_path=manifest_path,
                        manifest=manifest,
                        inspect_payload=inspect_payload,
                        handoff=handoff,
                        patch_replay=patch_replay,
                        status_flags=status_flags,
                    )
                )
    bindings.sort(key=lambda binding: _binding_sort_key(binding), reverse=True)
    return bindings


def make_session_key(context: ExtractedContext) -> str:
    if context.session_id:
        suffix = context.session_id
    elif context.transcript_path is not None:
        digest = hashlib.sha1(context.transcript_path.as_posix().encode("utf-8")).hexdigest()[:12]
        suffix = f"path-{digest}"
    else:
        digest_source = "|".join(
            [
                context.tool,
                context.source_kind,
                context.updated_at or "",
                context.title or "",
                context.cwd or "",
            ]
        )
        suffix = f"context-{hashlib.sha1(digest_source.encode('utf-8')).hexdigest()[:12]}"
    return f"{context.tool}:{context.source_kind}:{suffix}"


def _collect_contexts(project_root: Path, *, include_codex: bool, include_claude: bool) -> dict[str, list[ExtractedContext]]:
    candidates: dict[str, list[ExtractedContext]] = {}
    if include_codex:
        candidates["codex"] = collect_codex_contexts(project_root, limit=20)
    if include_claude:
        candidates["claude"] = collect_claude_contexts(project_root, limit=20)
    return candidates


def _load_sync_config_if_present(project_root: Path) -> SyncConfig | None:
    config_path = project_root / SYNC_DIR / "config.toml"
    if not config_path.exists():
        return None
    try:
        return load_sync_config(project_root)
    except SystemExit:
        return None


def _load_latest_pointer_if_exists(sync_root: Path, tool: str) -> dict[str, object] | None:
    latest_path = _latest_pointer_path(sync_root, tool)
    if not latest_path.exists():
        return None
    return json.loads(latest_path.read_text(encoding="utf-8"))


def _summarize_latest_state(latest_payload: dict[str, object] | None) -> tuple[str, str | None, list[str]]:
    if latest_payload is None:
        return "missing", None, []
    if latest_payload.get("requires_selection"):
        candidates = [item for item in latest_payload.get("candidates", []) if isinstance(item, str)]
        return "conflict", None, candidates
    snapshot_id = latest_payload.get("snapshot_id")
    return "ready", snapshot_id if isinstance(snapshot_id, str) else None, [
        snapshot_id
    ] if isinstance(snapshot_id, str) else []


def _load_json_if_exists(path: Path | None) -> dict[str, object] | None:
    if path is None or not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _match_manifest_for_context(
    sync_root: Path,
    tool: str,
    context: ExtractedContext,
    latest_payload: dict[str, object] | None,
) -> tuple[Path | None, dict[str, object] | None]:
    manifests_dir = sync_root / "manifests"
    if not manifests_dir.exists():
        return None, None

    manifests: list[tuple[Path, dict[str, object]]] = []
    for manifest_path in manifests_dir.glob("*.json"):
        manifest = _load_json_if_exists(manifest_path)
        if manifest is None:
            continue
        source = manifest.get("source", {})
        manifest_tool = source.get("tool") if isinstance(source, dict) else None
        if manifest_tool != tool:
            continue
        manifests.append((manifest_path, manifest))

    exact = _find_manifest_match(manifests, context)
    if exact is not None:
        return exact

    if latest_payload is not None:
        manifest_rel = latest_payload.get("manifest")
        if isinstance(manifest_rel, str):
            latest_manifest_path = sync_root / manifest_rel
            latest_manifest = _load_json_if_exists(latest_manifest_path)
            if latest_manifest is not None:
                return latest_manifest_path, latest_manifest

    return None, None


def _find_manifest_match(
    manifests: list[tuple[Path, dict[str, object]]],
    context: ExtractedContext,
) -> tuple[Path, dict[str, object]] | None:
    for manifest_path, manifest in manifests:
        for entry in _manifest_contexts(manifest):
            if _manifest_context_matches(entry, context):
                return manifest_path, manifest
    return None


def _manifest_contexts(manifest: dict[str, object]) -> list[dict[str, object]]:
    source = manifest.get("source", {})
    contexts = source.get("contexts") if isinstance(source, dict) else None
    if not isinstance(contexts, list):
        return []
    return [entry for entry in contexts if isinstance(entry, dict)]


def _manifest_context_matches(entry: dict[str, object], context: ExtractedContext) -> bool:
    session_id = entry.get("session_id")
    transcript_path = entry.get("transcript_path")
    if isinstance(session_id, str) and context.session_id and session_id == context.session_id:
        return True
    if isinstance(transcript_path, str) and context.transcript_path is not None:
        return transcript_path == context.transcript_path.as_posix()
    return False


def _load_handoff_payload(sync_root: Path, manifest: dict[str, object] | None) -> dict[str, object] | None:
    if manifest is None:
        return None
    artifacts = manifest.get("artifacts", {})
    handoff_rel = artifacts.get("handoff") if isinstance(artifacts, dict) else None
    if not isinstance(handoff_rel, str) or not handoff_rel.strip():
        return None
    handoff_path = sync_root / handoff_rel
    if not handoff_path.exists():
        return None
    markdown = handoff_path.read_text(encoding="utf-8")
    return {
        "path": handoff_rel,
        "format": "markdown",
        "title": _parse_handoff_title(markdown),
        "updated_at": _manifest_created_at(manifest),
        "current_goal": _parse_handoff_section(markdown, "Current Goal"),
        "summary": _handoff_summary(markdown),
        "markdown": markdown,
    }


def _patch_replay_payload(
    *,
    project_root: Path,
    tool: str,
    health: PatchReplayHealth,
    manifest: dict[str, object] | None,
    manifest_matches_latest: bool,
) -> dict[str, object]:
    if manifest is None:
        return _patch_replay_health_to_dict(health if manifest_matches_latest else _not_applicable_patch_replay())
    if manifest_matches_latest:
        return _patch_replay_health_to_dict(health)
    return _patch_replay_health_to_dict(_inspect_patch_replay_for_manifest(project_root, tool, manifest))


def _inspect_patch_replay_for_manifest(project_root: Path, tool: str, manifest: dict[str, object]) -> PatchReplayHealth:
    artifacts = manifest.get("artifacts", {})
    patch_rel = artifacts.get("patch") if isinstance(artifacts, dict) else None
    if not isinstance(patch_rel, str) or not patch_rel.strip():
        return PatchReplayHealth(
            state="none",
            patch_path=None,
            plain_apply_state="not-applicable",
            three_way_state="not-applicable",
            recommended_mode="none",
            recommended_reason="latest snapshot does not include a patch artifact",
            recommended_command=None,
        )

    project = manifest.get("project", {})
    exported_branch = project.get("branch") if isinstance(project, dict) and isinstance(project.get("branch"), str) else None
    exported_head = project.get("head") if isinstance(project, dict) and isinstance(project.get("head"), str) else None
    snapshot_id = manifest.get("snapshot_id") if isinstance(manifest.get("snapshot_id"), str) else None
    patch_path = project_root / SYNC_DIR / patch_rel
    check = inspect_patch(
        project_root,
        patch_path,
        exported_branch=exported_branch,
        exported_head=exported_head,
    )
    plain_apply_state = _plain_apply_state(check)
    three_way_state = _three_way_state(check)
    recommended_mode, recommended_reason = _recommend_patch_mode(check)
    state = "blocked" if check.project_dirty else "ready"
    if not check.patch_exists:
        state = "missing"
        recommended_mode = None
        recommended_reason = "patch artifact is referenced by the snapshot but missing locally"
    elif not check.project_is_git_repo:
        state = "unavailable"
        recommended_mode = None
        recommended_reason = "current checkout is not a Git worktree"
    elif recommended_mode is None:
        state = "unavailable"
    if check.project_dirty and recommended_reason:
        recommended_reason = (
            f"{recommended_reason} Current worktree is dirty, so replay stays blocked until you clean it up or pass --allow-dirty."
        )
    elif check.project_dirty:
        recommended_reason = "Current worktree is dirty, so replay stays blocked until you clean it up or pass --allow-dirty."
    return PatchReplayHealth(
        state=state,
        patch_path=patch_path,
        plain_apply_state=plain_apply_state,
        three_way_state=three_way_state,
        recommended_mode=recommended_mode,
        recommended_reason=recommended_reason,
        recommended_command=_recommended_patch_command(tool, snapshot_id, recommended_mode),
    )


def _not_applicable_patch_replay() -> PatchReplayHealth:
    return PatchReplayHealth(
        state="not-applicable",
        patch_path=None,
        plain_apply_state="not-applicable",
        three_way_state="not-applicable",
        recommended_mode=None,
        recommended_reason=None,
        recommended_command=None,
    )


def _patch_replay_health_to_dict(health: PatchReplayHealth) -> dict[str, object]:
    return {
        "state": health.state,
        "patch_path": health.patch_path.as_posix() if health.patch_path is not None else None,
        "plain_apply_state": health.plain_apply_state,
        "three_way_state": health.three_way_state,
        "recommended_mode": health.recommended_mode,
        "recommended_reason": health.recommended_reason,
        "recommended_command": health.recommended_command,
    }


def _plain_apply_state(check) -> str:
    if check.patch_path is None:
        return "not-applicable"
    if not check.patch_exists or not check.project_is_git_repo:
        return "unavailable"
    return "ok" if check.check_ok is True else "failed"


def _three_way_state(check) -> str:
    if check.patch_path is None:
        return "not-applicable"
    if not check.patch_exists or not check.project_is_git_repo:
        return "unavailable"
    if check.three_way_check_ok is not True:
        return "failed"
    return "conflicts" if check.three_way_check_conflicts else "ok"


def _recommend_patch_mode(check) -> tuple[str | None, str | None]:
    if check.check_ok is True:
        return PATCH_MODE_APPLY, "Plain patch replay is clean on the current checkout."
    if check.three_way_check_ok is True and check.three_way_check_conflicts:
        return PATCH_MODE_BRANCH, "3-way replay is possible, but it is likely to need conflict resolution, so isolating it on a temporary branch is safer."
    if check.three_way_check_ok is True:
        return PATCH_MODE_THREE_WAY, "Plain apply fails, but 3-way replay can still merge on the current checkout."
    return None, "Neither plain apply nor 3-way replay is available on the current checkout."


def _recommended_patch_command(tool: str, snapshot_id: str | None, mode: str | None) -> str | None:
    if not snapshot_id:
        return None
    if mode == PATCH_MODE_APPLY:
        return f"aiss import --tool {tool} --snapshot {snapshot_id} --apply-patch"
    if mode == PATCH_MODE_THREE_WAY:
        return f"aiss import --tool {tool} --snapshot {snapshot_id} --apply-patch --patch-mode 3way"
    if mode == PATCH_MODE_BRANCH:
        branch_name = default_patch_branch_name(snapshot_id)
        return (
            f"aiss import --tool {tool} --snapshot {snapshot_id} --apply-patch "
            f"--patch-mode branch --patch-branch {branch_name}"
        )
    return None


def _derive_status_flags(
    *,
    latest_state: str,
    manifest: dict[str, object] | None,
    patch_replay: dict[str, object],
) -> list[str]:
    flags: list[str] = []
    if latest_state == "conflict":
        flags.append("conflict")
    if manifest is not None:
        project = manifest.get("project", {})
        if isinstance(project, dict) and project.get("dirty") is True:
            flags.append("dirty")
        artifacts = manifest.get("artifacts", {})
        if isinstance(artifacts, dict) and isinstance(artifacts.get("patch"), str) and artifacts.get("patch"):
            flags.append("patch")
        redaction = manifest.get("redaction", {})
        warnings = redaction.get("warnings") if isinstance(redaction, dict) else None
        if isinstance(warnings, list) and warnings:
            flags.append("warning")
    elif patch_replay.get("state") not in {"none", "not-applicable"}:
        flags.append("patch")
    return flags


def _session_catalog_entry(binding: SessionBinding) -> dict[str, object]:
    context = binding.context
    return {
        "session_key": binding.session_key,
        "tool": context.tool,
        "source_kind": context.source_kind,
        "native_session_id": context.session_id,
        "title": context.title,
        "native_title": context.title,
        "project_id": binding.project_id,
        "project_label": binding.project_label,
        "updated_at": context.updated_at,
        "transcript_path": context.transcript_path.as_posix() if context.transcript_path else None,
        "cwd": context.cwd,
        "score": context.score,
        "score_reasons": context.score_reasons,
        "goal_candidate": context.goal_candidate,
        "excerpt_count": context.excerpt_count,
        "total_excerpt_count": context.total_excerpt_count,
        "total_user_count": context.total_user_count,
        "total_assistant_count": context.total_assistant_count,
        "latest_state": binding.latest_state,
        "latest_snapshot_id": binding.latest_snapshot_id,
        "has_handoff": binding.handoff is not None,
        "has_patch": "patch" in binding.status_flags,
        "patch_replay_state": binding.patch_replay["state"],
        "status_flags": binding.status_flags,
    }


def _session_detail_entry(binding: SessionBinding) -> dict[str, object]:
    context = binding.context
    return {
        "session_key": binding.session_key,
        "tool": context.tool,
        "source_kind": context.source_kind,
        "native_session_id": context.session_id,
        "title": context.title,
        "native_title": context.title,
        "project_id": binding.project_id,
        "project_label": binding.project_label,
        "updated_at": context.updated_at,
        "transcript_path": context.transcript_path.as_posix() if context.transcript_path else None,
        "cwd": context.cwd,
        "goal_candidate": context.goal_candidate,
        "score": context.score,
        "score_reasons": context.score_reasons,
        "excerpt_count": context.excerpt_count,
        "total_excerpt_count": context.total_excerpt_count,
        "total_user_count": context.total_user_count,
        "total_assistant_count": context.total_assistant_count,
        "raw_message_count": context.total_excerpt_count,
        "selected_excerpt_count": len(context.excerpts),
        "all_excerpt_count": len(context.all_excerpts),
        "device_id": _manifest_source_value(binding.manifest, "device_id"),
        "provider_profile": _manifest_source_value(binding.manifest, "provider_profile"),
        "latest_state": binding.latest_state,
        "latest_snapshot_id": binding.latest_snapshot_id,
        "latest_candidates": binding.latest_candidates,
        "has_handoff": binding.handoff is not None,
        "has_patch": "patch" in binding.status_flags,
        "patch_replay_state": binding.patch_replay["state"],
        "status_flags": binding.status_flags,
    }


def _build_project_summaries(bindings: list[SessionBinding]) -> list[dict[str, object]]:
    grouped = _group_bindings_by_project(bindings)
    projects = []
    for project_id, group in grouped.items():
        projects.append(
            {
                "project_id": project_id,
                "display_name": group[0].project_label,
                "session_count": len(group),
                "tool_counts": _tool_counts(group),
                "latest_updated_at": _latest_updated_at(group),
                "roots": _unique_roots(group),
            }
        )
    projects.sort(key=lambda item: item["display_name"])
    return projects


def _project_catalog_entry(project_id: str, group: list[SessionBinding]) -> dict[str, object]:
    latest_snapshot_ids = {"codex": None, "claude": None}
    latest_conflicts: dict[str, list[str]] = {"codex": [], "claude": []}
    for tool in SUPPORTED_DESKTOP_TOOLS:
        tool_bindings = [binding for binding in group if binding.tool == tool]
        if not tool_bindings:
            continue
        latest_snapshot_ids[tool] = tool_bindings[0].latest_snapshot_id
        if tool_bindings[0].latest_state == "conflict":
            latest_conflicts[tool] = list(tool_bindings[0].latest_candidates)
    sessions = [_project_session_entry(binding) for binding in group]
    recommended = _recommended_binding(group)
    return {
        "project_id": project_id,
        "display_name": group[0].project_label,
        "roots": _unique_roots(group),
        "git_remote": group[0].project_git.get("git_remote"),
        "branch": group[0].project_git.get("branch"),
        "head": group[0].project_git.get("head"),
        "session_count": len(group),
        "active_tools": sorted({binding.tool for binding in group}),
        "latest_snapshot_ids": latest_snapshot_ids,
        "latest_conflicts": latest_conflicts,
        "sessions": sessions,
        "recommended_session_key": recommended.session_key if recommended is not None else None,
    }


def _project_session_entry(binding: SessionBinding) -> dict[str, object]:
    return {
        "session_key": binding.session_key,
        "tool": binding.tool,
        "title": binding.context.title,
        "updated_at": binding.context.updated_at,
        "goal_candidate": binding.context.goal_candidate,
        "score": binding.context.score,
        "status_flags": binding.status_flags,
    }


def _recommended_binding(group: list[SessionBinding]) -> SessionBinding | None:
    if not group:
        return None
    return sorted(group, key=_binding_sort_key, reverse=True)[0]


def _binding_sort_key(binding: SessionBinding) -> tuple[int, int, float]:
    priority = 0
    if "conflict" in binding.status_flags:
        priority += 40
    if binding.patch_replay["state"] in {"ready", "blocked"}:
        priority += 20
    return (priority, binding.context.score, _timestamp(binding.context.updated_at))


def _tool_counts(bindings: list[SessionBinding]) -> dict[str, int]:
    counts = {tool: 0 for tool in SUPPORTED_DESKTOP_TOOLS}
    for binding in bindings:
        counts[binding.tool] += 1
    return counts


def _status_counts(bindings: list[SessionBinding]) -> dict[str, int]:
    tracked = ("dirty", "patch", "conflict", "warning")
    counts = {name: 0 for name in tracked}
    for binding in bindings:
        for flag in tracked:
            if flag in binding.status_flags:
                counts[flag] += 1
    return counts


def _group_bindings_by_project(bindings: list[SessionBinding]) -> dict[str, list[SessionBinding]]:
    grouped: dict[str, list[SessionBinding]] = defaultdict(list)
    for binding in bindings:
        grouped[binding.project_id].append(binding)
    for project_id in grouped:
        grouped[project_id] = sorted(grouped[project_id], key=_binding_sort_key, reverse=True)
    return dict(sorted(grouped.items(), key=lambda item: item[0]))


def _latest_updated_at(bindings: list[SessionBinding]) -> str | None:
    if not bindings:
        return None
    best = max(bindings, key=lambda binding: _timestamp(binding.context.updated_at))
    return best.context.updated_at


def _unique_roots(bindings: list[SessionBinding]) -> list[str]:
    seen: list[str] = []
    for binding in bindings:
        root = binding.project_root.as_posix()
        if root not in seen:
            seen.append(root)
    return seen


def _manifest_source_value(manifest: dict[str, object] | None, key: str) -> str | None:
    if manifest is None:
        return None
    source = manifest.get("source", {})
    value = source.get(key) if isinstance(source, dict) else None
    return value if isinstance(value, str) else None


def _manifest_created_at(manifest: dict[str, object]) -> str:
    created_at = manifest.get("created_at")
    if isinstance(created_at, str):
        return created_at
    return _generated_at()


def _parse_handoff_title(markdown: str) -> str:
    for line in markdown.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped[2:].strip() or "Session Handoff"
    return "Session Handoff"


def _parse_handoff_section(markdown: str, heading: str) -> str | None:
    lines = markdown.splitlines()
    target = f"## {heading}"
    for index, line in enumerate(lines):
        if line.strip() != target:
            continue
        values: list[str] = []
        for inner in lines[index + 1 :]:
            if inner.startswith("## "):
                break
            values.append(inner)
        text = "\n".join(values).strip()
        return text or None
    return None


def _handoff_summary(markdown: str) -> str | None:
    recent = _parse_handoff_section(markdown, "Recent Context Summary")
    if recent:
        first = [line.strip("- ").strip() for line in recent.splitlines() if line.strip()]
        if first:
            return first[0]
    goal = _parse_handoff_section(markdown, "Current Goal")
    return goal


def _generated_at() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _timestamp(value: str | None) -> float:
    if not value:
        return 0.0
    text = value
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(text).timestamp()
    except ValueError:
        return 0.0


def _latest_pointer_path(sync_root: Path, tool: str) -> Path:
    latest_path = sync_root / "latest" / f"{tool}.json"
    if latest_path.exists() or tool == "all":
        return latest_path
    fallback = sync_root / "latest" / "all.json"
    if fallback.exists():
        return fallback
    return latest_path


def _context_to_dict(context: ExtractedContext) -> dict[str, object]:
    selected_positions = _selected_excerpt_positions(context.excerpts, context.all_excerpts)
    selected_index_by_all_excerpt = {
        all_excerpt_index: selected_index
        for selected_index, all_excerpt_index in enumerate(selected_positions, start=1)
    }
    all_excerpt_index_by_selected = {
        selected_index: all_excerpt_index
        for selected_index, all_excerpt_index in enumerate(selected_positions, start=1)
    }
    return {
        "tool": context.tool,
        "source_kind": context.source_kind,
        "session_id": context.session_id,
        "title": context.title,
        "updated_at": context.updated_at,
        "cwd": context.cwd,
        "transcript_path": context.transcript_path.as_posix() if context.transcript_path else None,
        "score": context.score,
        "score_reasons": context.score_reasons,
        "goal_candidate": context.goal_candidate,
        "excerpt_count": context.excerpt_count,
        "total_excerpt_count": context.total_excerpt_count,
        "total_user_count": context.total_user_count,
        "total_assistant_count": context.total_assistant_count,
        "all_excerpts": [
            {
                "role": excerpt.role,
                "created_at": excerpt.created_at,
                "text": excerpt.text,
                "selected": excerpt_index in selected_index_by_all_excerpt,
                "selected_index": selected_index_by_all_excerpt.get(excerpt_index),
            }
            for excerpt_index, excerpt in enumerate(context.all_excerpts, start=1)
        ],
        "excerpts": [
            {
                "role": excerpt.role,
                "created_at": excerpt.created_at,
                "text": excerpt.text,
                "selected_index": excerpt_index,
                "all_excerpt_index": all_excerpt_index_by_selected.get(excerpt_index),
            }
            for excerpt_index, excerpt in enumerate(context.excerpts, start=1)
        ],
    }


def _selected_excerpt_positions(selected, all_excerpts) -> list[int]:
    positions_by_key: dict[tuple[str, str, str], list[int]] = defaultdict(list)
    for index, excerpt in enumerate(all_excerpts, start=1):
        positions_by_key[_excerpt_key(excerpt)].append(index)

    selected_positions: list[int] = []
    for excerpt in selected:
        positions = positions_by_key[_excerpt_key(excerpt)]
        if positions:
            selected_positions.append(positions.pop(0))
    return selected_positions


def _excerpt_key(excerpt) -> tuple[str, str, str]:
    return (excerpt.role, excerpt.created_at, excerpt.text)
