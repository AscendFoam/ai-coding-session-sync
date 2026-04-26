"""Patch inspection and application helpers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .project import git_info, run_git


@dataclass(frozen=True)
class PatchCheckResult:
    patch_path: Path | None
    patch_exists: bool
    project_is_git_repo: bool
    project_branch: str | None
    project_head: str | None
    project_dirty: bool | None
    exported_branch: str | None
    exported_head: str | None
    branch_matches: bool | None
    head_matches: bool | None
    check_ok: bool | None
    check_error: str | None


@dataclass(frozen=True)
class PatchApplyResult:
    patch_path: Path
    applied: bool
    check_ok: bool | None
    message: str


def inspect_patch(
    project_root: Path,
    patch_path: Path | None,
    *,
    exported_branch: str | None = None,
    exported_head: str | None = None,
) -> PatchCheckResult:
    info = git_info(project_root)
    project_branch = _normalize_git_value(info["branch"])
    project_head = _normalize_git_value(info["head"])
    branch_matches = _match_git_value(project_branch, exported_branch)
    head_matches = _match_git_value(project_head, exported_head)
    if patch_path is None:
        return PatchCheckResult(
            patch_path=None,
            patch_exists=False,
            project_is_git_repo=bool(info["is_git_repo"]),
            project_branch=project_branch,
            project_head=project_head,
            project_dirty=info["dirty"],
            exported_branch=exported_branch,
            exported_head=exported_head,
            branch_matches=branch_matches,
            head_matches=head_matches,
            check_ok=None,
            check_error=None,
        )

    patch_exists = patch_path.exists()
    if not patch_exists:
        return PatchCheckResult(
            patch_path=patch_path,
            patch_exists=False,
            project_is_git_repo=bool(info["is_git_repo"]),
            project_branch=project_branch,
            project_head=project_head,
            project_dirty=info["dirty"],
            exported_branch=exported_branch,
            exported_head=exported_head,
            branch_matches=branch_matches,
            head_matches=head_matches,
            check_ok=None,
            check_error="patch file does not exist",
        )

    if not info["is_git_repo"]:
        return PatchCheckResult(
            patch_path=patch_path,
            patch_exists=True,
            project_is_git_repo=False,
            project_branch=project_branch,
            project_head=project_head,
            project_dirty=info["dirty"],
            exported_branch=exported_branch,
            exported_head=exported_head,
            branch_matches=branch_matches,
            head_matches=head_matches,
            check_ok=None,
            check_error="current project is not a git repository",
        )

    code, out, err = run_git(["apply", "--check", str(patch_path)], project_root)
    return PatchCheckResult(
        patch_path=patch_path,
        patch_exists=True,
        project_is_git_repo=True,
        project_branch=project_branch,
        project_head=project_head,
        project_dirty=info["dirty"],
        exported_branch=exported_branch,
        exported_head=exported_head,
        branch_matches=branch_matches,
        head_matches=head_matches,
        check_ok=(code == 0),
        check_error=None if code == 0 else (err or out or "git apply --check failed"),
    )


def apply_patch(
    project_root: Path,
    patch_path: Path,
    *,
    allow_dirty: bool = False,
    exported_branch: str | None = None,
    exported_head: str | None = None,
) -> PatchApplyResult:
    check = inspect_patch(
        project_root,
        patch_path,
        exported_branch=exported_branch,
        exported_head=exported_head,
    )
    if not check.patch_exists:
        return PatchApplyResult(
            patch_path=patch_path,
            applied=False,
            check_ok=check.check_ok,
            message="Patch file does not exist.",
        )
    if not check.project_is_git_repo:
        return PatchApplyResult(
            patch_path=patch_path,
            applied=False,
            check_ok=check.check_ok,
            message="Patch apply requires a Git worktree.",
        )
    if check.project_dirty and not allow_dirty:
        return PatchApplyResult(
            patch_path=patch_path,
            applied=False,
            check_ok=check.check_ok,
            message="Refusing to apply patch to a dirty worktree. Commit, stash, or rerun with --allow-dirty.",
        )
    if check.check_ok is not True:
        return PatchApplyResult(
            patch_path=patch_path,
            applied=False,
            check_ok=check.check_ok,
            message=f"Patch does not apply cleanly: {check.check_error or 'git apply --check failed'}",
        )

    code, out, err = run_git(["apply", str(patch_path)], project_root)
    if code != 0:
        return PatchApplyResult(
            patch_path=patch_path,
            applied=False,
            check_ok=True,
            message=f"Patch apply failed: {err or out or 'git apply failed'}",
        )

    message = "Patch applied successfully."
    warnings: list[str] = []
    if allow_dirty and check.project_dirty:
        warnings.append("Applied with --allow-dirty; review overlapping local changes carefully.")
    if check.branch_matches is False or check.head_matches is False:
        warnings.append("Current checkout differs from the export snapshot, so review the resulting diff before continuing.")
    if warnings:
        message = f"{message} {' '.join(warnings)}"
    return PatchApplyResult(
        patch_path=patch_path,
        applied=True,
        check_ok=True,
        message=message,
    )


def _normalize_git_value(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    return normalized or None


def _match_git_value(current: str | None, exported: str | None) -> bool | None:
    if current is None or exported is None:
        return None
    return current == exported
