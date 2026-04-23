"""Handoff bundle generation and import prompt rendering."""

from __future__ import annotations

import json
from pathlib import Path


def render_handoff(
    *,
    goal: str,
    project: dict[str, object],
    tool: str,
    notes: str,
    patch_path: str | None,
) -> str:
    status = project.get("status_short") or "(clean or unavailable)"
    patch_line = patch_path or "(not exported)"
    return f"""# Session Handoff

## Current Goal

{goal or "Continue the current project work."}

## Project State

- Tool: {tool}
- Repository: {project.get("git_remote") or "(no git remote detected)"}
- Branch: {project.get("branch") or "(unknown)"}
- HEAD: {project.get("head") or "(unknown)"}
- Dirty worktree: {project.get("dirty")}
- Patch: {patch_line}

## Completed Work

- No adapter-specific transcript extraction has run yet.

## Important Decisions

- Use handoff-first sync instead of relying on fragile cross-account native resume.
- Do not sync authentication data.

## Relevant Files

- `${{PROJECT_ROOT}}`: current project root.

## Open Questions

- Which Codex and Claude Code native transcript formats should be supported first?
- Which remote sync backend should be enabled first for real cross-device use?

## Next Steps

1. Review this handoff on the target device.
2. Apply the patch manually if needed.
3. Start a fresh AI coding session and provide the generated bootstrap prompt.

## Constraints

- Do not assume the target device uses the same account or provider.
- Do not copy auth files, tokens, or global credentials.

## Verification

- Git status at export time:

```text
{status}
```

## Notes

{notes or "(none)"}
"""


def render_excerpts(*, goal: str, notes: str, created_at: str) -> str:
    records = []
    if goal:
        records.append({"role": "user", "created_at": created_at, "text": goal})
    if notes:
        records.append({"role": "user", "created_at": created_at, "text": notes})
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
