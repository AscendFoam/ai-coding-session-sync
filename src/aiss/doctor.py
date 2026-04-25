"""Sync health diagnostics for CLI status and doctor output."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

from .config import SyncConfig
from .project import run_git
from .schema import SYNC_DIR


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
    issues: tuple[str, ...]
    next_steps: tuple[str, ...]


def inspect_sync_health(project_root: Path, config: SyncConfig | None, *, tool: str = "all") -> SyncHealth:
    sync_root = project_root / SYNC_DIR
    latest_path = _latest_pointer_path(sync_root, tool)
    latest_payload = _load_json_if_exists(latest_path) if latest_path is not None else None

    latest_state = "missing"
    latest_snapshot_id = None
    latest_candidates: tuple[str, ...] = ()
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
