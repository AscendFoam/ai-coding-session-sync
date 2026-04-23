"""Small first-pass redaction helpers."""

from __future__ import annotations

import re

SECRET_PATTERNS = (
    re.compile(r"sk-[A-Za-z0-9_\-]{20,}"),
    re.compile(r"sk-ant-[A-Za-z0-9_\-]{20,}"),
    re.compile(r"github_pat_[A-Za-z0-9_]{20,}"),
    re.compile(r"gh[pousr]_[A-Za-z0-9_]{20,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"(?i)(bearer\s+)[A-Za-z0-9._\-]{20,}"),
)


def redact_text(text: str) -> str:
    redacted = text
    for pattern in SECRET_PATTERNS:
        redacted = pattern.sub(lambda match: _replacement(match.group(0)), redacted)
    return redacted


def _replacement(value: str) -> str:
    if value.lower().startswith("bearer "):
        return "Bearer [REDACTED]"
    return "[REDACTED]"
