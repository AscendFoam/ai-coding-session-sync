"""Sync health diagnostics for CLI status and doctor output."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

from .config import SyncConfig
from .patching import (
    PATCH_MODE_APPLY,
    PATCH_MODE_BRANCH,
    PATCH_MODE_THREE_WAY,
    default_patch_branch_name,
    inspect_patch,
)
from .project import run_git
from .schema import SYNC_DIR


@dataclass(frozen=True)
class PatchReplayHealth:
    state: str
    patch_path: Path | None
    plain_apply_state: str
    three_way_state: str
    recommended_mode: str | None
    recommended_reason: str | None
    recommended_command: str | None


@dataclass(frozen=True)
class SyncHealth:
    sync_dir_present: bool
    config_present: bool
    backend_name: str | None
    storage: str | None
    sidecar_remote: str | None
    sidecar_branch: str | None
    sidecar_remote_configured: bool
    sidecar_remote_reachable: bool | None
    sidecar_remote_branch_exists: bool | None
    latest_path: Path | None
    latest_state: str
    latest_snapshot_id: str | None
    latest_candidates: tuple[str, ...]
    patch_replay: PatchReplayHealth
    issues: tuple[str, ...]
    next_steps: tuple[str, ...]


def inspect_sync_health(project_root: Path, config: SyncConfig | None, *, tool: str = "all") -> SyncHealth:
    sync_root = project_root / SYNC_DIR
    latest_path = _latest_pointer_path(sync_root, tool)
    latest_payload = _load_json_if_exists(latest_path) if latest_path is not None else None

    latest_state = "missing"
    latest_snapshot_id = None
    latest_candidates: tuple[str, ...] = ()
    patch_replay = PatchReplayHealth(
        state="not-applicable",
        patch_path=None,
        plain_apply_state="not-applicable",
        three_way_state="not-applicable",
        recommended_mode=None,
        recommended_reason=None,
        recommended_command=None,
    )
    if latest_payload is not None:
        if latest_payload.get("requires_selection"):
            latest_state = "conflict"
            latest_candidates = tuple(
                candidate for candidate in latest_payload.get("candidates", []) if isinstance(candidate, str)
            )
        else:
            latest_state = "ready"
            snapshot_id = latest_payload.get("snapshot_id")
            latest_snapshot_id = snapshot_id if isinstance(snapshot_id, str) else None
            patch_replay = _inspect_patch_replay(sync_root, latest_payload, tool, project_root)

    issues: list[str] = []
    next_steps: list[str] = []
    backend_name = config.backend_name if config is not None else None
    storage = config.storage if config is not None else None
    sidecar_remote = config.git.remote if config is not None and config.git is not None else None
    sidecar_branch = config.git.branch if config is not None and config.git is not None else None
    sidecar_remote_configured = bool(sidecar_remote)
    sidecar_remote_reachable: bool | None = None
    sidecar_remote_branch_exists: bool | None = None

    if not sync_root.exists():
        issues.append("sync dir is missing")
        next_steps.append("Run `aiss init` in this project.")

    if config is None:
        issues.append("sync config is missing")
        next_steps.append("Run `aiss init` to create .ai-session-sync/config.toml.")
    elif storage == "sidecar-repo" or backend_name == "git":
        if not sidecar_remote_configured:
            issues.append("sidecar git remote is not configured")
            next_steps.append("Set `[backend.git].remote` in `.ai-session-sync/config.toml`.")
        else:
            sidecar_remote_reachable, sidecar_remote_branch_exists, remote_error = _probe_git_remote(
                sync_root,
                sidecar_remote or "",
                sidecar_branch or "main",
            )
            if sidecar_remote_reachable is False:
                issues.append(f"sidecar remote is not reachable: {remote_error}")
                next_steps.append("Check the sidecar remote URL and your Git access.")
            elif sidecar_remote_branch_exists is False:
                issues.append("sidecar remote branch does not exist yet")
                next_steps.append("Run `aiss push` to create the first sidecar branch.")

    if latest_state == "missing":
        issues.append("latest pointer is missing")
        next_steps.append("Run `aiss export --tool codex|claude` or `aiss pull` to create sync state.")
    elif latest_state == "conflict":
        issues.append("latest pointer requires selection")
        resolve_tool = tool if tool != "all" else _suggest_latest_tool(latest_path)
        next_steps.append(f"Run `aiss latest resolve --tool {resolve_tool} <snapshot_id>`.")
    elif patch_replay.state == "missing":
        issues.append("latest snapshot patch artifact is missing locally")
    elif patch_replay.state == "blocked":
        issues.append("patch replay is blocked by the current dirty worktree")
    elif patch_replay.state == "unavailable":
        issues.append("patch replay is not available on the current checkout")

    if patch_replay.recommended_command:
        next_steps.append(f"Patch replay suggestion: run `{patch_replay.recommended_command}`.")

    return SyncHealth(
        sync_dir_present=sync_root.exists(),
        config_present=config is not None,
        backend_name=backend_name,
        storage=storage,
        sidecar_remote=sidecar_remote,
        sidecar_branch=sidecar_branch,
        sidecar_remote_configured=sidecar_remote_configured,
        sidecar_remote_reachable=sidecar_remote_reachable,
        sidecar_remote_branch_exists=sidecar_remote_branch_exists,
        latest_path=latest_path,
        latest_state=latest_state,
        latest_snapshot_id=latest_snapshot_id,
        latest_candidates=latest_candidates,
        patch_replay=patch_replay,
        issues=tuple(_dedupe(issues)),
        next_steps=tuple(_dedupe(next_steps)),
    )


def _probe_git_remote(sync_root: Path, remote: str, branch: str) -> tuple[bool, bool | None, str | None]:
    probe_root = sync_root / "tmp"
    probe_root.mkdir(parents=True, exist_ok=True)
    code, out, err = run_git(["ls-remote", "--heads", remote, branch], probe_root)
    if code != 0:
        return False, None, (err or out or "unknown git error")
    return True, bool(out.strip()), None


def _latest_pointer_path(sync_root: Path, tool: str) -> Path | None:
    if tool == "all":
        candidates = [sync_root / "latest" / name for name in ("all.json", "codex.json", "claude.json")]
    else:
        candidates = [sync_root / "latest" / f"{tool}.json", sync_root / "latest" / "all.json"]

    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0] if candidates else None


def _load_json_if_exists(path: Path | None) -> dict[str, object] | None:
    if path is None or not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _inspect_patch_replay(
    sync_root: Path,
    latest_payload: dict[str, object],
    requested_tool: str,
    project_root: Path,
) -> PatchReplayHealth:
    manifest_rel = latest_payload.get("manifest")
    if not isinstance(manifest_rel, str) or not manifest_rel.strip():
        return PatchReplayHealth(
            state="not-applicable",
            patch_path=None,
            plain_apply_state="not-applicable",
            three_way_state="not-applicable",
            recommended_mode=None,
            recommended_reason=None,
            recommended_command=None,
        )

    manifest_path = sync_root / manifest_rel
    manifest = _load_json_if_exists(manifest_path)
    if manifest is None:
        return PatchReplayHealth(
            state="unavailable",
            patch_path=manifest_path,
            plain_apply_state="unavailable",
            three_way_state="unavailable",
            recommended_mode=None,
            recommended_reason="latest manifest is missing locally",
            recommended_command=None,
        )

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
    patch_path = sync_root / patch_rel
    check = inspect_patch(
        project_root,
        patch_path,
        exported_branch=exported_branch,
        exported_head=exported_head,
    )
    return _summarize_patch_replay(check, manifest, requested_tool)


def _summarize_patch_replay(
    check,
    manifest: dict[str, object],
    requested_tool: str,
) -> PatchReplayHealth:
    plain_apply_state = _plain_apply_state(check)
    three_way_state = _three_way_state(check)
    snapshot_id = manifest.get("snapshot_id") if isinstance(manifest.get("snapshot_id"), str) else None
    tool = _resolve_manifest_tool(manifest, requested_tool)

    if check.patch_path is None:
        return PatchReplayHealth(
            state="none",
            patch_path=None,
            plain_apply_state=plain_apply_state,
            three_way_state=three_way_state,
            recommended_mode="none",
            recommended_reason="latest snapshot does not include a patch artifact",
            recommended_command=None,
        )

    if not check.patch_exists:
        return PatchReplayHealth(
            state="missing",
            patch_path=check.patch_path,
            plain_apply_state=plain_apply_state,
            three_way_state=three_way_state,
            recommended_mode=None,
            recommended_reason="patch artifact is referenced by the latest snapshot but missing locally",
            recommended_command=None,
        )

    if not check.project_is_git_repo:
        return PatchReplayHealth(
            state="unavailable",
            patch_path=check.patch_path,
            plain_apply_state=plain_apply_state,
            three_way_state=three_way_state,
            recommended_mode=None,
            recommended_reason="current checkout is not a Git worktree",
            recommended_command=None,
        )

    recommended_mode, recommended_reason = _recommend_patch_mode(check)
    state = "blocked" if check.project_dirty else "ready"
    if recommended_mode is None:
        state = "unavailable"

    if recommended_reason and check.project_dirty:
        recommended_reason = (
            f"{recommended_reason} Current worktree is dirty, so replay stays blocked until you clean it up or pass --allow-dirty."
        )
    elif check.project_dirty:
        recommended_reason = "Current worktree is dirty, so replay stays blocked until you clean it up or pass --allow-dirty."

    command = _recommended_patch_command(tool, snapshot_id, recommended_mode) if snapshot_id and recommended_mode in {
        PATCH_MODE_APPLY,
        PATCH_MODE_THREE_WAY,
        PATCH_MODE_BRANCH,
    } else None

    return PatchReplayHealth(
        state=state,
        patch_path=check.patch_path,
        plain_apply_state=plain_apply_state,
        three_way_state=three_way_state,
        recommended_mode=recommended_mode,
        recommended_reason=recommended_reason,
        recommended_command=command,
    )


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


def _recommended_patch_command(tool: str, snapshot_id: str, mode: str | None) -> str | None:
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


def _resolve_manifest_tool(manifest: dict[str, object], requested_tool: str) -> str:
    if requested_tool in {"codex", "claude"}:
        return requested_tool
    source = manifest.get("source", {})
    tool = source.get("tool") if isinstance(source, dict) else None
    if isinstance(tool, str) and tool in {"codex", "claude"}:
        return tool
    snapshot_id = manifest.get("snapshot_id")
    if isinstance(snapshot_id, str):
        if snapshot_id.endswith("-codex"):
            return "codex"
        if snapshot_id.endswith("-claude"):
            return "claude"
    return "all"


def _suggest_latest_tool(path: Path | None) -> str:
    if path is None:
        return "all"
    stem = path.stem
    return stem if stem in {"all", "codex", "claude"} else "all"


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        ordered.append(item)
    return ordered
