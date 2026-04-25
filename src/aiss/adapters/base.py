"""Shared adapter models and helpers."""

from __future__ import annotations

import os
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
    warnings: list[str] = field(default_factory=list)

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
