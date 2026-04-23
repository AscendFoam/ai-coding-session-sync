"""Shared schema constants for AI Coding Session Sync."""

from __future__ import annotations

SCHEMA_VERSION = "0.1.0"
SYNC_DIR = ".ai-session-sync"
DEFAULT_TOOL = "all"
SUPPORTED_TOOLS = ("all", "codex", "claude")

CONFIG_TEMPLATE = """schema_version = "0.1.0"
project_id = "{project_id}"
storage = "ignored-local"

[backend.local]
path = ".ai-session-sync"

[tools.codex]
enabled = true
mode = "handoff"
codex_home = "auto"
include_native = false

[tools.claude]
enabled = true
mode = "handoff"
claude_home = "auto"
include_native = false
include_memory = true

[redaction]
enabled = true
ruleset = "default"

[encryption]
enabled = false
provider = "age"
"""
