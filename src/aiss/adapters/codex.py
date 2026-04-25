"""Codex transcript extraction."""

from __future__ import annotations

import json
import os
from pathlib import Path

from .base import Excerpt, ExtractedContext, clean_text, normalize_project_text, path_within_project
from ..redaction import redact_text


def extract_codex_context(project_root: Path, *, max_messages: int = 10) -> ExtractedContext | None:
    codex_home = _resolve_codex_home()
    sessions_root = codex_home / "sessions"
    if not sessions_root.exists():
        return None

    titles = _load_session_titles(codex_home / "session_index.jsonl")
    candidates = sorted(
        [path for path in sessions_root.rglob("*.jsonl") if path.is_file()],
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )

    for transcript_path in candidates:
        context = _parse_candidate(transcript_path, project_root, titles, max_messages=max_messages)
        if context is not None:
            return context
    return None


def _resolve_codex_home() -> Path:
    env_value = os.environ.get("AISS_CODEX_HOME") or os.environ.get("CODEX_HOME")
    if env_value:
        return Path(env_value).expanduser().resolve(strict=False)
    return (Path.home() / ".codex").resolve(strict=False)


def _load_session_titles(index_path: Path) -> dict[str, str]:
    titles: dict[str, str] = {}
    if not index_path.exists():
        return titles
    with index_path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            session_id = record.get("id")
            if isinstance(session_id, str):
                title = record.get("thread_name")
                if isinstance(title, str) and title.strip():
                    titles[session_id] = title.strip()
    return titles


def _parse_candidate(
    transcript_path: Path,
    project_root: Path,
    titles: dict[str, str],
    *,
    max_messages: int,
) -> ExtractedContext | None:
    session_id: str | None = None
    cwd: str | None = None
    updated_at: str | None = None
    excerpts: list[Excerpt] = []

    with transcript_path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            record_type = record.get("type")
            payload = record.get("payload", {})
            if record_type == "session_meta" and isinstance(payload, dict):
                session_id = _string(payload.get("id")) or session_id
                cwd = _string(payload.get("cwd")) or cwd
                updated_at = _string(record.get("timestamp")) or updated_at
                continue
            if record_type != "response_item" or not isinstance(payload, dict):
                continue
            if payload.get("type") != "message":
                continue
            role = payload.get("role")
            if role not in {"user", "assistant"}:
                continue
            text = _extract_message_text(role, payload.get("content", []))
            text = _filter_codex_text(text)
            if not text:
                continue
            text = clean_text(redact_text(normalize_project_text(text, project_root)))
            if not text:
                continue
            excerpts.append(
                Excerpt(
                    role=role,
                    created_at=_string(record.get("timestamp")) or updated_at or "",
                    text=text,
                    tool="codex",
                    session_id=session_id,
                )
            )
            updated_at = _string(record.get("timestamp")) or updated_at

    if not path_within_project(cwd, project_root):
        return None
    if not excerpts:
        return None
    excerpts = excerpts[-max_messages:]
    return ExtractedContext(
        tool="codex",
        source_kind="transcript",
        session_id=session_id,
        transcript_path=transcript_path,
        cwd=cwd,
        title=titles.get(session_id or ""),
        updated_at=updated_at,
        excerpts=excerpts,
    )


def _extract_message_text(role: str, blocks: object) -> str:
    if not isinstance(blocks, list):
        return ""
    allowed = {"user": {"input_text"}, "assistant": {"output_text"}}[role]
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


def _filter_codex_text(text: str) -> str:
    stripped = text.strip()
    if not stripped:
        return ""
    if stripped.startswith("<environment_context>"):
        return ""
    return stripped


def _string(value: object) -> str | None:
    return value if isinstance(value, str) else None
