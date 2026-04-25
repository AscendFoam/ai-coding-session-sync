"""Claude Code transcript extraction."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from .base import Excerpt, ExtractedContext, clean_text, normalize_project_text, path_within_project
from ..redaction import redact_text


def extract_claude_context(project_root: Path, *, max_messages: int = 10) -> ExtractedContext | None:
    claude_home = _resolve_claude_home()
    projects_root = claude_home / "projects"
    if projects_root.exists():
        candidates = sorted(
            [path for path in projects_root.rglob("*.jsonl") if path.is_file()],
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        for transcript_path in candidates:
            context = _parse_candidate(transcript_path, project_root, max_messages=max_messages)
            if context is not None:
                return context

    history_path = claude_home / "history.jsonl"
    return _extract_from_history(history_path, project_root, max_messages=max_messages)


def _resolve_claude_home() -> Path:
    env_value = os.environ.get("AISS_CLAUDE_HOME")
    if env_value:
        return Path(env_value).expanduser().resolve(strict=False)
    return (Path.home() / ".claude").resolve(strict=False)


def _parse_candidate(transcript_path: Path, project_root: Path, *, max_messages: int) -> ExtractedContext | None:
    excerpts: list[Excerpt] = []
    session_id: str | None = None
    cwd: str | None = None
    updated_at: str | None = None

    with transcript_path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            if record.get("type") not in {"user", "assistant"}:
                continue
            message = record.get("message")
            if not isinstance(message, dict):
                continue
            role = message.get("role")
            if role not in {"user", "assistant"}:
                continue
            cwd = _string(record.get("cwd")) or cwd
            session_id = _string(record.get("sessionId")) or session_id
            updated_at = _string(record.get("timestamp")) or updated_at
            text = _extract_message_text(role, message.get("content", []))
            text = _filter_claude_text(text)
            if not text:
                continue
            text = clean_text(redact_text(normalize_project_text(text, project_root)))
            if not text:
                continue
            excerpts.append(
                Excerpt(
                    role=role,
                    created_at=_string(record.get("timestamp")) or "",
                    text=text,
                    tool="claude",
                    session_id=session_id,
                )
            )

    if not path_within_project(cwd, project_root):
        return None
    if not excerpts:
        return None
    excerpts = excerpts[-max_messages:]
    return ExtractedContext(
        tool="claude",
        source_kind="transcript",
        session_id=session_id,
        transcript_path=transcript_path,
        cwd=cwd,
        title=transcript_path.stem,
        updated_at=updated_at,
        excerpts=excerpts,
    )


def _extract_from_history(history_path: Path, project_root: Path, *, max_messages: int) -> ExtractedContext | None:
    if not history_path.exists():
        return None

    excerpts: list[Excerpt] = []
    updated_at: str | None = None
    with history_path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not path_within_project(_string(record.get("project")), project_root):
                continue
            text = _string(record.get("display")) or ""
            text = _filter_claude_text(text)
            if not text:
                continue
            created_at = _history_timestamp_to_iso(record.get("timestamp"))
            updated_at = created_at or updated_at
            excerpts.append(
                Excerpt(
                    role="user",
                    created_at=created_at or "",
                    text=clean_text(redact_text(normalize_project_text(text, project_root))),
                    tool="claude",
                    session_id=None,
                )
            )

    if not excerpts:
        return None
    excerpts = excerpts[-max_messages:]
    return ExtractedContext(
        tool="claude",
        source_kind="history",
        session_id=None,
        transcript_path=history_path,
        cwd=str(project_root),
        title="history",
        updated_at=updated_at,
        excerpts=excerpts,
    )


def _extract_message_text(role: str, blocks: object) -> str:
    if not isinstance(blocks, list):
        return ""
    allowed = {"user": {"text"}, "assistant": {"text"}}[role]
    parts: list[str] = []
    for block in blocks:
        if not isinstance(block, dict):
            continue
        if block.get("type") not in allowed:
            continue
        text = _string(block.get("text"))
        if text:
            parts.append(text)
    return "\n\n".join(parts).strip()


def _filter_claude_text(text: str) -> str:
    stripped = text.strip()
    if not stripped or stripped == "/clear":
        return ""
    return stripped


def _history_timestamp_to_iso(value: object) -> str | None:
    if not isinstance(value, int):
        return None
    return datetime.fromtimestamp(value / 1000, tz=timezone.utc).isoformat()


def _string(value: object) -> str | None:
    return value if isinstance(value, str) else None
