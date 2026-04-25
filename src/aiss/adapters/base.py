"""Shared adapter models and helpers."""

from __future__ import annotations

import os
from datetime import datetime
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(slots=True)
class Excerpt:
    role: str
    created_at: str
    text: str
    tool: str
    session_id: str | None = None


@dataclass(slots=True)
class ExtractedContext:
    tool: str
    source_kind: str
    session_id: str | None
    transcript_path: Path | None
    cwd: str | None
    title: str | None
    updated_at: str | None
    excerpts: list[Excerpt] = field(default_factory=list)
    all_excerpts: list[Excerpt] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    total_excerpt_count: int = 0
    total_user_count: int = 0
    total_assistant_count: int = 0
    goal_candidate: str | None = None
    score: int = 0
    score_reasons: list[str] = field(default_factory=list)

    @property
    def excerpt_count(self) -> int:
        return len(self.excerpts)

    @property
    def latest_user_text(self) -> str | None:
        for excerpt in reversed(self.excerpts):
            if excerpt.role == "user" and excerpt.text:
                return excerpt.text
        return None

    @property
    def latest_assistant_text(self) -> str | None:
        for excerpt in reversed(self.excerpts):
            if excerpt.role == "assistant" and excerpt.text:
                return excerpt.text
        return None


def path_within_project(candidate: str | None, project_root: Path) -> bool:
    if not candidate:
        return False
    try:
        candidate_path = Path(candidate).expanduser().resolve(strict=False)
        root = project_root.expanduser().resolve(strict=False)
    except OSError:
        return False
    if candidate_path == root:
        return True
    return root in candidate_path.parents


def path_match_rank(candidate: str | None, project_root: Path) -> int:
    if not candidate:
        return 0
    try:
        candidate_variants = _path_variants(Path(candidate))
        project_variants = _path_variants(project_root)
    except OSError:
        return 0
    if candidate_variants & project_variants:
        return 2
    if path_within_project(candidate, project_root):
        return 1
    return 0


def normalize_project_text(text: str, project_root: Path) -> str:
    normalized = text
    variants = _path_variants(project_root)
    for variant in sorted(variants, key=len, reverse=True):
        if variant:
            normalized = normalized.replace(variant, "${PROJECT_ROOT}")
    return normalized


def _path_variants(path: Path) -> set[str]:
    expanded = path.expanduser()
    raw_variants = {
        expanded.as_posix(),
        str(expanded),
        str(expanded).replace("\\", "/"),
        expanded.resolve(strict=False).as_posix(),
        str(expanded.resolve(strict=False)),
        str(expanded.resolve(strict=False)).replace("\\", "/"),
        os.path.abspath(str(expanded)),
        os.path.abspath(str(expanded)).replace("\\", "/"),
        os.path.realpath(str(expanded)),
        os.path.realpath(str(expanded)).replace("\\", "/"),
    }
    variants: set[str] = set()
    for variant in raw_variants:
        if not variant:
            continue
        variants.add(variant)
        if variant.startswith("/private/"):
            variants.add(variant[len("/private") :])
        elif variant.startswith("/var/"):
            variants.add("/private" + variant)
    return variants


def clean_text(text: str, *, max_chars: int = 1400) -> str:
    cleaned = text.replace("\r\n", "\n").strip()
    if len(cleaned) > max_chars:
        cleaned = cleaned[: max_chars - 1].rstrip() + "…"
    return cleaned


def extract_request_text(text: str) -> str:
    markers = (
        "## My request for Codex:",
        "## My request for Claude:",
        "My request for Codex:",
        "My request for Claude:",
    )
    for marker in markers:
        if marker in text:
            return text.split(marker, 1)[1].strip()
    return text.strip()


def derive_goal_candidate(excerpts: list[Excerpt], *, fallback_title: str | None = None) -> str | None:
    for excerpt in reversed(excerpts):
        if excerpt.role != "user" or not excerpt.text:
            continue
        candidate = clean_text(extract_request_text(excerpt.text), max_chars=240)
        if candidate:
            return candidate
    if fallback_title:
        return clean_text(fallback_title, max_chars=240)
    return None


def select_representative_excerpts(excerpts: list[Excerpt], *, max_messages: int) -> list[Excerpt]:
    if len(excerpts) <= max_messages:
        return list(excerpts)

    last_user_index = None
    for index in range(len(excerpts) - 1, -1, -1):
        if excerpts[index].role == "user":
            last_user_index = index
            break

    if last_user_index is None:
        return excerpts[-max_messages:]

    tail = excerpts[last_user_index:]
    if len(tail) >= max_messages:
        if max_messages == 1:
            return [tail[0]]
        return [tail[0], *tail[-(max_messages - 1) :]]

    needed_before = max_messages - len(tail)
    before_start = max(0, last_user_index - needed_before)
    return excerpts[before_start:last_user_index] + tail


def enrich_context(context: ExtractedContext, project_root: Path, *, max_messages: int) -> ExtractedContext:
    all_excerpts = list(context.excerpts)
    context.all_excerpts = list(all_excerpts)
    context.total_excerpt_count = len(all_excerpts)
    context.total_user_count = sum(1 for excerpt in all_excerpts if excerpt.role == "user")
    context.total_assistant_count = sum(1 for excerpt in all_excerpts if excerpt.role == "assistant")
    context.goal_candidate = derive_goal_candidate(all_excerpts, fallback_title=context.title)
    context.excerpts = select_representative_excerpts(all_excerpts, max_messages=max_messages)
    context.score, context.score_reasons = score_context(context, project_root)
    return context


def score_context(context: ExtractedContext, project_root: Path) -> tuple[int, list[str]]:
    score = 0
    reasons: list[str] = []

    match_rank = path_match_rank(context.cwd, project_root)
    if match_rank == 2:
        score += 120
        reasons.append("cwd exactly matches project root")
    elif match_rank == 1:
        score += 90
        reasons.append("cwd is inside project root")
    else:
        score -= 100
        reasons.append("cwd does not match project root")

    if context.total_user_count:
        user_bonus = min(context.total_user_count, 3) * 25
        score += user_bonus
        reasons.append(f"{context.total_user_count} user excerpt(s)")
    else:
        score -= 40
        reasons.append("no user excerpts")

    if context.total_assistant_count:
        assistant_bonus = min(context.total_assistant_count, 6) * 6
        score += assistant_bonus
        reasons.append(f"{context.total_assistant_count} assistant excerpt(s)")

    if context.goal_candidate:
        score += 30
        reasons.append("goal candidate available")

    if context.title:
        score += 5
        reasons.append("title available")

    if context.updated_at:
        score += 10
        reasons.append("updated timestamp available")

    return score, reasons


def context_sort_key(context: ExtractedContext) -> tuple[float, int, int, int]:
    return (
        iso_to_timestamp(context.updated_at),
        context.total_user_count,
        context.total_excerpt_count,
        context.score,
    )


def iso_to_timestamp(value: str | None) -> float:
    if not value:
        return 0.0
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(text).timestamp()
    except ValueError:
        return 0.0
