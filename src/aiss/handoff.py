"""Handoff bundle generation and import prompt rendering."""

from __future__ import annotations

import json
from pathlib import Path

from .adapters import ExtractedContext, Excerpt
from .redaction import redact_text
from .adapters.base import normalize_project_text


def render_handoff(
    *,
    goal: str,
    project: dict[str, object],
    tool: str,
    notes: str,
    patch_path: str | None,
    contexts: list[ExtractedContext],
    project_root: Path,
) -> str:
    status = project.get("status_short") or "(clean or unavailable)"
    patch_line = patch_path or "(not exported)"
    normalized_goal = _normalize_handoff_text(goal, project_root) or "Continue the current project work."
    completed_work = _render_completed_work(contexts, project_root)
    recent_context = _render_recent_context(contexts, project_root)
    important_decisions = _render_important_decisions(notes)
    relevant_files = _render_relevant_files(contexts, project_root)
    open_questions = _render_open_questions(contexts)
    next_steps = _render_next_steps(contexts)
    notes_block = _render_notes(notes, contexts, project_root)
    return f"""# Session Handoff

## Current Goal

{normalized_goal}

## Project State

- Tool: {tool}
- Repository: {project.get("git_remote") or "(no git remote detected)"}
- Branch: {project.get("branch") or "(unknown)"}
- HEAD: {project.get("head") or "(unknown)"}
- Dirty worktree: {project.get("dirty")}
- Patch: {patch_line}

## Completed Work

{completed_work}

## Recent Context Summary

{recent_context}

## Important Decisions

{important_decisions}

## Relevant Files

{relevant_files}

## Open Questions

{open_questions}

## Next Steps

{next_steps}

## Constraints

- Do not assume the target device uses the same account or provider.
- Do not copy auth files, tokens, or global credentials.

## Verification

- Git status at export time:

```text
{status}
```

## Notes

{notes_block}
"""


def render_excerpts(excerpts: list[Excerpt]) -> str:
    records = [
        {
            "role": excerpt.role,
            "created_at": excerpt.created_at,
            "text": excerpt.text,
            "tool": excerpt.tool,
            "session_id": excerpt.session_id,
        }
        for excerpt in excerpts
    ]
    return "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records)


def render_import_prompt(handoff_path: Path, excerpts_path: Path | None) -> str:
    handoff = handoff_path.read_text(encoding="utf-8")
    excerpts = ""
    if excerpts_path and excerpts_path.exists():
        excerpts = excerpts_path.read_text(encoding="utf-8").strip()
    return f"""请继续这个项目。你正在从另一个设备的 AI coding 会话交接过来。

当前机器可能使用不同账号、不同 provider 或不同本地路径。不要假设可以原生恢复同一个 session。

以下是项目交接信息：

{handoff}

以下是最近对话摘录：

```jsonl
{excerpts or "(none)"}
```

请先简要确认你理解的当前状态、未完成事项和下一步计划，然后继续推进。
"""


def render_patch_guidance(
    *,
    patch_path: str | None,
    patch_exists: bool,
    project_is_git_repo: bool,
    project_branch: str | None,
    project_head: str | None,
    project_dirty: bool | None,
    exported_branch: str | None,
    exported_head: str | None,
    branch_matches: bool | None,
    head_matches: bool | None,
    check_ok: bool | None,
    check_error: str | None,
    three_way_check_ok: bool | None,
    three_way_check_conflicts: bool | None,
    three_way_check_error: str | None,
    apply_command: str,
    three_way_command: str,
    branch_command: str,
) -> str:
    if not patch_path:
        return "Patch status: no patch artifact was exported for this snapshot."

    lines = [f"Patch status: `{patch_path}`"]
    if not patch_exists:
        lines.append("- Patch file is missing locally.")
        return "\n".join(lines)

    if not project_is_git_repo:
        lines.append("- Current project is not a Git worktree, so patch apply is unavailable.")
        return "\n".join(lines)

    lines.append(f"- Export branch: `{exported_branch or '(unknown)'}`")
    lines.append(f"- Current branch: `{project_branch or '(unknown)'}`")
    if branch_matches is False:
        lines.append("- Branch differs from the export snapshot.")
    lines.append(f"- Export HEAD: `{exported_head or '(unknown)'}`")
    lines.append(f"- Current HEAD: `{project_head or '(unknown)'}`")
    if head_matches is False:
        lines.append("- HEAD differs from the export snapshot.")
    lines.append(f"- Current worktree dirty: {project_dirty}")
    if check_ok is True:
        lines.append("- `git apply --check` succeeded.")
        if three_way_check_ok is True:
            if three_way_check_conflicts:
                lines.append("- `git apply --3way --check` can recover by merging, but it expects conflict review.")
            else:
                lines.append("- `git apply --3way --check` also succeeds.")
        if project_dirty:
            lines.append(f"- To replay it anyway, run `{apply_command} --allow-dirty` after reviewing your local changes.")
        else:
            lines.append(f"- Safe path: run `{apply_command}` if you want to replay the uncommitted work now.")
        lines.append(f"- Safer isolation path: run `{branch_command}` to replay it on a temporary branch.")
    elif check_ok is False:
        lines.append(f"- `git apply --check` failed: {check_error}")
        if three_way_check_ok is True:
            if three_way_check_conflicts:
                lines.append("- `git apply --3way --check` can proceed by merging, but conflict resolution will still be needed.")
            else:
                lines.append("- `git apply --3way --check` succeeds, so a 3-way replay may still work.")
            lines.append(f"- Try `{three_way_command}` if you want Git to attempt a merge in the current worktree.")
            lines.append(f"- Safer isolation path: run `{branch_command}` to do that replay on a temporary branch instead.")
        else:
            if three_way_check_error:
                lines.append(f"- `git apply --3way --check` also failed: {three_way_check_error}")
            lines.append("- Review the handoff first; patch replay is not safe until the mismatch is resolved.")
    else:
        lines.append("- Patch apply readiness was not checked.")
    return "\n".join(lines)


def _render_completed_work(contexts: list[ExtractedContext], project_root: Path) -> str:
    if not contexts:
        return "- No local transcript context was found; this handoff uses only direct CLI inputs and Git state."
    lines = []
    for context in contexts:
        source = context.transcript_path.as_posix() if context.transcript_path else "(unknown)"
        source = _normalize_handoff_text(source, project_root)
        title = f" `{context.title}`" if context.title else ""
        lines.append(
            f"- Extracted {context.excerpt_count} recent transcript entries from local `{context.tool}` {context.source_kind}{title} at `{source}`."
        )
    return "\n".join(lines)


def _render_recent_context(contexts: list[ExtractedContext], project_root: Path) -> str:
    if not contexts:
        return "- No recent transcript summary available."
    lines = []
    for context in contexts:
        latest_user = _normalize_handoff_text(context.latest_user_text or "(no recent user text found)", project_root)
        latest_assistant = _normalize_handoff_text(
            context.latest_assistant_text or "(no recent assistant text found)",
            project_root,
        )
        lines.append(f"- `{context.tool}` latest user message: {latest_user}")
        lines.append(f"- `{context.tool}` latest assistant message: {latest_assistant}")
    return "\n".join(lines)


def _render_important_decisions(notes: str) -> str:
    lines = [
        "- Use handoff-first sync instead of relying on fragile cross-account native resume.",
        "- Do not sync authentication data.",
    ]
    if notes:
        lines.append("- Preserve the exporter-provided notes below as operator context.")
    return "\n".join(lines)


def _render_relevant_files(contexts: list[ExtractedContext], project_root: Path) -> str:
    lines = ["- `${PROJECT_ROOT}`: current project root."]
    for context in contexts:
        if context.cwd:
            cwd = _normalize_handoff_text(context.cwd, project_root)
            lines.append(f"- `{context.tool}` cwd at export time: `{cwd}`.")
    return "\n".join(lines)


def _render_open_questions(contexts: list[ExtractedContext]) -> str:
    if any(context.source_kind == "transcript" for context in contexts):
        return "\n".join(
            [
                "- Which remote sync backend should be enabled first for real cross-device use?",
                "- How much of native transcript replay should remain experimental versus default handoff behavior?",
            ]
        )
    return "\n".join(
        [
            "- No matching local transcript was found for this project; should the operator provide a manual goal or notes?",
            "- Should history-only fallback be enabled or expanded for this tool on this machine?",
        ]
    )


def _render_next_steps(contexts: list[ExtractedContext]) -> str:
    lines = [
        "1. Review this handoff on the target device.",
        "2. Apply the patch manually if needed.",
        "3. Start a fresh AI coding session and provide the generated bootstrap prompt.",
    ]
    if contexts:
        lines.append("4. Compare the imported prompt with the recent transcript excerpt to avoid repeating completed work.")
    return "\n".join(lines)


def _render_notes(notes: str, contexts: list[ExtractedContext], project_root: Path) -> str:
    lines = []
    if notes:
        lines.append(_normalize_handoff_text(notes, project_root))
    for context in contexts:
        session = context.session_id or "(unknown session)"
        location = context.transcript_path.as_posix() if context.transcript_path else "(unknown path)"
        location = _normalize_handoff_text(location, project_root)
        lines.append(
            f"Source: `{context.tool}` {context.source_kind}, session `{session}`, transcript `{location}`."
        )
    return "\n\n".join(lines) if lines else "(none)"


def _normalize_handoff_text(text: str, project_root: Path) -> str:
    return redact_text(normalize_project_text(text, project_root))
