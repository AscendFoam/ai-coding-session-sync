"""Git-backed sidecar sync."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
import json
from pathlib import Path
import shutil
import tempfile

from ..config import GitBackendConfig
from ..project import run_git
from ..schema import SYNC_DIR

SYNC_ARTIFACT_DIRS = ("manifests", "handoffs", "excerpts", "patches", "latest", "native")


@dataclass(frozen=True)
class GitSyncResult:
    remote: str
    branch: str
    copied_files: int
    latest_files: tuple[str, ...]
    commit_created: bool
    commit_id: str | None = None
    remote_has_branch: bool = True


def pull_git_sidecar(project_root: Path, config: GitBackendConfig) -> GitSyncResult:
    sync_root = project_root / SYNC_DIR
    with _prepared_repo(sync_root, config) as prepared:
        if not prepared.remote_has_branch:
            return GitSyncResult(
                remote=config.remote,
                branch=config.branch,
                copied_files=0,
                latest_files=(),
                commit_created=False,
                commit_id=None,
                remote_has_branch=False,
            )

        copied_files = _copy_sync_dirs(prepared.repo_path, sync_root, include_latest=False)
        latest_files = _merge_latest_dirs(sync_root / "latest", prepared.repo_path / "latest", sync_root / "latest")
        return GitSyncResult(
            remote=config.remote,
            branch=config.branch,
            copied_files=copied_files,
            latest_files=tuple(latest_files),
            commit_created=False,
            commit_id=None,
            remote_has_branch=True,
        )


def push_git_sidecar(project_root: Path, config: GitBackendConfig) -> GitSyncResult:
    sync_root = project_root / SYNC_DIR
    with _prepared_repo(sync_root, config) as prepared:
        copied_files = _copy_sync_dirs(sync_root, prepared.repo_path, include_latest=False)
        latest_files = _merge_latest_dirs(prepared.repo_path / "latest", sync_root / "latest", prepared.repo_path / "latest")
        commit_created = False
        commit_id = None

        status_code, status_out, status_err = run_git(["status", "--short"], prepared.repo_path)
        if status_code != 0:
            raise SystemExit(f"Could not inspect sidecar git status: {status_err or status_out}")

        if status_out:
            _require_git_ok(run_git(["add", "."], prepared.repo_path), "Could not stage sidecar sync files.")
            _require_git_ok(
                run_git(["commit", "-m", "aiss sync update"], prepared.repo_path),
                "Could not commit sidecar sync files.",
            )
            commit_created = True
            head_code, head_out, head_err = run_git(["rev-parse", "--short", "HEAD"], prepared.repo_path)
            if head_code != 0:
                raise SystemExit(f"Could not read sidecar commit id: {head_err or head_out}")
            commit_id = head_out
            _require_git_ok(
                run_git(["push", "-u", "origin", config.branch], prepared.repo_path),
                "Could not push sidecar sync files.",
            )

        return GitSyncResult(
            remote=config.remote,
            branch=config.branch,
            copied_files=copied_files,
            latest_files=tuple(latest_files),
            commit_created=commit_created,
            commit_id=commit_id,
            remote_has_branch=prepared.remote_has_branch,
        )


@dataclass(frozen=True)
class _PreparedRepo:
    repo_path: Path
    remote_has_branch: bool


@contextmanager
def _prepared_repo(sync_root: Path, config: GitBackendConfig):
    tmp_root = sync_root / "tmp"
    tmp_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=tmp_root) as tmp:
        repo_path = Path(tmp)
        _require_git_ok(run_git(["init"], repo_path), "Could not initialize temporary sidecar git repo.")
        _require_git_ok(run_git(["config", "user.name", "AI Session Sync"], repo_path), "Could not configure sidecar git user.")
        _require_git_ok(
            run_git(["config", "user.email", "aiss@local.invalid"], repo_path),
            "Could not configure sidecar git email.",
        )
        _require_git_ok(
            run_git(["remote", "add", "origin", config.remote], repo_path),
            f"Could not add sidecar git remote '{config.remote}'.",
        )

        remote_has_branch = _remote_branch_exists(repo_path, config)
        if remote_has_branch:
            _require_git_ok(
                run_git(["fetch", "origin", config.branch], repo_path),
                f"Could not fetch sidecar branch '{config.branch}'.",
            )
            _require_git_ok(
                run_git(["checkout", "-B", config.branch, "FETCH_HEAD"], repo_path),
                f"Could not checkout sidecar branch '{config.branch}'.",
            )
        else:
            _require_git_ok(
                run_git(["checkout", "-B", config.branch], repo_path),
                f"Could not create sidecar branch '{config.branch}'.",
            )

        yield _PreparedRepo(repo_path=repo_path, remote_has_branch=remote_has_branch)


def _remote_branch_exists(repo_path: Path, config: GitBackendConfig) -> bool:
    code, out, err = run_git(["ls-remote", "--exit-code", "--heads", "origin", config.branch], repo_path)
    if code == 0:
        return bool(out.strip())
    if code == 2:
        return False
    raise SystemExit(f"Could not inspect sidecar git remote '{config.remote}': {err or out}")


def _copy_sync_dirs(src_root: Path, dst_root: Path, *, include_latest: bool) -> int:
    copied_files = 0
    for dirname in SYNC_ARTIFACT_DIRS:
        if dirname == "latest" and not include_latest:
            continue
        copied_files += _copy_tree(src_root / dirname, dst_root / dirname)
    return copied_files


def _copy_tree(src_dir: Path, dst_dir: Path) -> int:
    if not src_dir.exists():
        return 0

    copied_files = 0
    for src_path in src_dir.rglob("*"):
        if src_path.is_dir():
            continue
        target_path = dst_dir / src_path.relative_to(src_dir)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        if not target_path.exists() or target_path.read_bytes() != src_path.read_bytes():
            shutil.copy2(src_path, target_path)
            copied_files += 1
    return copied_files


def _merge_latest_dirs(primary_dir: Path, secondary_dir: Path, target_dir: Path) -> list[str]:
    names = set()
    if primary_dir.exists():
        names.update(path.name for path in primary_dir.glob("*.json"))
    if secondary_dir.exists():
        names.update(path.name for path in secondary_dir.glob("*.json"))

    updated = []
    for name in sorted(names):
        merged = _merge_latest_payload(
            _read_json_if_exists(primary_dir / name),
            _read_json_if_exists(secondary_dir / name),
        )
        if merged is None:
            continue
        content = json.dumps(merged, indent=2) + "\n"
        target_path = target_dir / name
        target_path.parent.mkdir(parents=True, exist_ok=True)
        if not target_path.exists() or target_path.read_text(encoding="utf-8") != content:
            target_path.write_text(content, encoding="utf-8")
            updated.append(name)
    return updated


def _merge_latest_payload(primary: dict[str, object] | None, secondary: dict[str, object] | None) -> dict[str, object] | None:
    if primary is None:
        return secondary
    if secondary is None:
        return primary
    if primary == secondary:
        return primary

    primary_candidates = _pointer_candidates(primary)
    secondary_candidates = _pointer_candidates(secondary)
    if _is_conflict_pointer(primary) or _is_conflict_pointer(secondary):
        return {
            "candidates": sorted(set(primary_candidates + secondary_candidates), reverse=True),
            "requires_selection": True,
        }

    winner = max(primary_candidates + secondary_candidates)
    return {
        "snapshot_id": winner,
        "manifest": f"manifests/{winner}.json",
    }


def _pointer_candidates(payload: dict[str, object]) -> list[str]:
    snapshot_id = payload.get("snapshot_id")
    if isinstance(snapshot_id, str):
        return [snapshot_id]
    candidates = payload.get("candidates")
    if isinstance(candidates, list):
        return [candidate for candidate in candidates if isinstance(candidate, str)]
    return []


def _is_conflict_pointer(payload: dict[str, object]) -> bool:
    return bool(payload.get("requires_selection"))


def _read_json_if_exists(path: Path) -> dict[str, object] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _require_git_ok(result: tuple[int, str, str], message: str) -> None:
    code, out, err = result
    if code != 0:
        raise SystemExit(f"{message} {err or out}".strip())
