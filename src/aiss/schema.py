"""Shared schema constants for AI Coding Session Sync."""

from __future__ import annotations

SCHEMA_VERSION = "0.1.0"
SYNC_DIR = ".ai-session-sync"
DEFAULT_TOOL = "all"
SUPPORTED_TOOLS = ("all", "codex", "claude")
DEFAULT_BACKEND = "local"
SUPPORTED_BACKENDS = ("local", "git")
DEFAULT_STORAGE = "ignored-local"
SUPPORTED_STORAGES = ("ignored-local", "in-repo", "sidecar-repo")


def render_config_template(
    project_id: str,
    *,
    storage: str = DEFAULT_STORAGE,
    backend: str = DEFAULT_BACKEND,
    remote: str = "",
    branch: str = "main",
) -> str:
    quoted_project_id = _quote_toml_string(project_id)
    lines = [
        f'schema_version = "{SCHEMA_VERSION}"',
        f'project_id = "{quoted_project_id}"',
        f'storage = "{storage}"',
        "",
    ]

    if backend == "git":
        lines.extend(
            [
                "[backend.git]",
                f'remote = "{_quote_toml_string(remote)}"',
                f'branch = "{_quote_toml_string(branch)}"',
                "",
            ]
        )
    else:
        lines.extend(
            [
                "[backend.local]",
                'path = ".ai-session-sync"',
                "",
            ]
        )

    lines.extend(
        [
            "[tools.codex]",
            "enabled = true",
            'mode = "handoff"',
            'codex_home = "auto"',
            "include_native = false",
            "",
            "[tools.claude]",
            "enabled = true",
            'mode = "handoff"',
            'claude_home = "auto"',
            "include_native = false",
            "include_memory = true",
            "",
            "[redaction]",
            "enabled = true",
            'ruleset = "default"',
            "",
            "[encryption]",
            "enabled = false",
            'provider = "age"',
            "",
        ]
    )
    return "\n".join(lines)


def _quote_toml_string(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')
