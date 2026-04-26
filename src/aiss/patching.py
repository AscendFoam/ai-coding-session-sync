"""Patch inspection and application helpers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

from .project import git_info, run_git

PATCH_MODE_APPLY = "apply"
PATCH_MODE_THREE_WAY = "3way"
PATCH_MODE_BRANCH = "branch"
PATCH_MODES = (PATCH_MODE_APPLY, PATCH_MODE_THREE_WAY, PATCH_MODE_BRANCH)


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
    three_way_check_ok: bool | None
    three_way_check_conflicts: bool | None
    three_way_check_error: str | None


@dataclass(frozen=True)
class PatchApplyResult:
    patch_path: Path
    applied: bool
    check_ok: bool | None
    mode: str
    branch_name: str | None
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
            three_way_check_ok=None,
            three_way_check_conflicts=None,
            three_way_check_error=None,
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
            three_way_check_ok=None,
            three_way_check_conflicts=None,
            three_way_check_error=None,
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
            three_way_check_ok=None,
            three_way_check_conflicts=None,
            three_way_check_error=None,
        )

    code, out, err = run_git(["apply", "--check", str(patch_path)], project_root)
    three_way_code, three_way_out, three_way_err = run_git(["apply", "--3way", "--check", str(patch_path)], project_root)
    three_way_note = (three_way_err or three_way_out or "").strip()
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
        three_way_check_ok=(three_way_code == 0),
        three_way_check_conflicts=("with conflicts" in three_way_note.lower()) if three_way_code == 0 else None,
        three_way_check_error=None if three_way_code == 0 else (three_way_err or three_way_out or "git apply --3way --check failed"),
    )


def apply_patch(
    project_root: Path,
    patch_path: Path,
    *,
    mode: str = PATCH_MODE_APPLY,
    allow_dirty: bool = False,
    exported_branch: str | None = None,
    exported_head: str | None = None,
    branch_name: str | None = None,
    snapshot_id: str | None = None,
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
            mode=mode,
            branch_name=None,
            message="Patch file does not exist.",
        )
    if not check.project_is_git_repo:
        return PatchApplyResult(
            patch_path=patch_path,
            applied=False,
            check_ok=check.check_ok,
            mode=mode,
            branch_name=None,
            message="Patch apply requires a Git worktree.",
        )
    if check.project_dirty and not allow_dirty:
        return PatchApplyResult(
            patch_path=patch_path,
            applied=False,
            check_ok=check.check_ok,
            mode=mode,
            branch_name=None,
            message="Refusing to apply patch to a dirty worktree. Commit, stash, or rerun with --allow-dirty.",
        )
    if mode not in PATCH_MODES:
        return PatchApplyResult(
            patch_path=patch_path,
            applied=False,
            check_ok=check.check_ok,
            mode=mode,
            branch_name=None,
            message=f"Unknown patch mode: {mode}",
        )

    if mode == PATCH_MODE_APPLY:
        return _apply_direct_patch(project_root, patch_path, check, allow_dirty=allow_dirty)
    if mode == PATCH_MODE_THREE_WAY:
        return _apply_three_way_patch(project_root, patch_path, check, allow_dirty=allow_dirty)
    return _apply_patch_on_branch(
        project_root,
        patch_path,
        check,
        allow_dirty=allow_dirty,
        branch_name=branch_name,
        snapshot_id=snapshot_id,
    )


def default_patch_branch_name(snapshot_id: str) -> str:
    slug = re.sub(r"[^a-z0-9._-]+", "-", snapshot_id.strip().lower()).strip("._-")
    return f"aiss/import-{slug or 'snapshot'}"


def _apply_direct_patch(
    project_root: Path,
    patch_path: Path,
    check: PatchCheckResult,
    *,
    allow_dirty: bool,
) -> PatchApplyResult:
    if check.check_ok is not True:
        extra = ""
        if check.three_way_check_ok:
            extra = " Try `--patch-mode 3way` or the safer `--patch-mode branch`."
        message = f"Patch does not apply cleanly: {check.check_error or 'git apply --check failed'}"
        if extra:
            message += extra
        return PatchApplyResult(
            patch_path=patch_path,
            applied=False,
            check_ok=check.check_ok,
            mode=PATCH_MODE_APPLY,
            branch_name=None,
            message=message,
        )

    code, out, err = run_git(["apply", str(patch_path)], project_root)
    if code != 0:
        return PatchApplyResult(
            patch_path=patch_path,
            applied=False,
            check_ok=True,
            mode=PATCH_MODE_APPLY,
            branch_name=None,
            message=f"Patch apply failed: {err or out or 'git apply failed'}",
        )
    message = _success_message("Patch applied successfully.", check, allow_dirty=allow_dirty)
    return PatchApplyResult(
        patch_path=patch_path,
        applied=True,
        check_ok=True,
        mode=PATCH_MODE_APPLY,
        branch_name=None,
        message=message,
    )


def _apply_three_way_patch(
    project_root: Path,
    patch_path: Path,
    check: PatchCheckResult,
    *,
    allow_dirty: bool,
) -> PatchApplyResult:
    if check.three_way_check_ok is not True:
        return PatchApplyResult(
            patch_path=patch_path,
            applied=False,
            check_ok=check.check_ok,
            mode=PATCH_MODE_THREE_WAY,
            branch_name=None,
            message=f"Patch 3-way apply is not available: {check.three_way_check_error or 'git apply --3way --check failed'}",
        )

    code, out, err = run_git(["apply", "--3way", str(patch_path)], project_root)
    if code != 0:
        detail = err or out or "git apply --3way failed"
        return PatchApplyResult(
            patch_path=patch_path,
            applied=False,
            check_ok=check.check_ok,
            mode=PATCH_MODE_THREE_WAY,
            branch_name=None,
            message=(
                "Patch 3-way apply left conflicts in the current worktree: "
                f"{detail}. Consider rerunning with `--patch-mode branch` to isolate the conflict resolution."
            ),
        )
    message = _success_message("Patch applied with --3way successfully.", check, allow_dirty=allow_dirty)
    return PatchApplyResult(
        patch_path=patch_path,
        applied=True,
        check_ok=check.check_ok,
        mode=PATCH_MODE_THREE_WAY,
        branch_name=None,
        message=message,
    )


def _apply_patch_on_branch(
    project_root: Path,
    patch_path: Path,
    check: PatchCheckResult,
    *,
    allow_dirty: bool,
    branch_name: str | None,
    snapshot_id: str | None,
) -> PatchApplyResult:
    if check.check_ok is not True and check.three_way_check_ok is not True:
        return PatchApplyResult(
            patch_path=patch_path,
            applied=False,
            check_ok=check.check_ok,
            mode=PATCH_MODE_BRANCH,
            branch_name=None,
            message="Patch cannot be applied directly or via 3-way merge on the current checkout.",
        )

    resolved_branch = branch_name or default_patch_branch_name(snapshot_id or patch_path.stem)
    code, out, err = run_git(["checkout", "-b", resolved_branch], project_root)
    if code != 0:
        return PatchApplyResult(
            patch_path=patch_path,
            applied=False,
            check_ok=check.check_ok,
            mode=PATCH_MODE_BRANCH,
            branch_name=resolved_branch,
            message=f"Could not create temporary branch '{resolved_branch}': {err or out or 'git checkout -b failed'}",
        )

    if check.check_ok is True:
        apply_args = ["apply", str(patch_path)]
        success_prefix = f"Created branch '{resolved_branch}' and applied the patch there successfully."
    else:
        apply_args = ["apply", "--3way", str(patch_path)]
        success_prefix = f"Created branch '{resolved_branch}' and applied the patch there with --3way."

    code, out, err = run_git(apply_args, project_root)
    if code != 0:
        detail = err or out or "git apply failed"
        if "with conflicts" in detail.lower():
            return PatchApplyResult(
                patch_path=patch_path,
                applied=True,
                check_ok=check.check_ok,
                mode=PATCH_MODE_BRANCH,
                branch_name=resolved_branch,
                message=(
                    f"Created branch '{resolved_branch}' and replayed the patch there, but manual conflict resolution is still needed: "
                    f"{detail}"
                ),
            )
        return PatchApplyResult(
            patch_path=patch_path,
            applied=False,
            check_ok=check.check_ok,
            mode=PATCH_MODE_BRANCH,
            branch_name=resolved_branch,
            message=(
                f"Created branch '{resolved_branch}', but patch replay still needs manual resolution there: "
                f"{detail}"
            ),
        )

    message = _success_message(success_prefix, check, allow_dirty=allow_dirty, branch_name=resolved_branch)
    return PatchApplyResult(
        patch_path=patch_path,
        applied=True,
        check_ok=check.check_ok,
        mode=PATCH_MODE_BRANCH,
        branch_name=resolved_branch,
        message=message,
    )


def _success_message(
    prefix: str,
    check: PatchCheckResult,
    *,
    allow_dirty: bool,
    branch_name: str | None = None,
) -> str:
    warnings: list[str] = []
    if allow_dirty and check.project_dirty:
        warning = "Applied with --allow-dirty; review overlapping local changes carefully."
        if branch_name:
            warning = (
                f"Created branch '{branch_name}' from a dirty worktree; review both the carried local changes and the imported patch carefully."
            )
        warnings.append(warning)
    if check.branch_matches is False or check.head_matches is False:
        warnings.append("Current checkout differs from the export snapshot, so review the resulting diff before continuing.")
    if warnings:
        return f"{prefix} {' '.join(warnings)}"
    return prefix


def _normalize_git_value(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    return normalized or None


def _match_git_value(current: str | None, exported: str | None) -> bool | None:
    if current is None or exported is None:
        return None
    return current == exported
