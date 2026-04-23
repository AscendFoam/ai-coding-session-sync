# Claude Code Adapter Plan

The Claude Code adapter extracts project-relevant context from local Claude Code state and converts it into the project-bound handoff protocol.

## First Version

The first version should:

- scan `~/.claude/projects/`;
- parse project-related JSONL transcripts when available;
- optionally include project `CLAUDE.md`;
- optionally include project memory;
- normalize paths to `${PROJECT_ROOT}`;
- generate a Claude-specific bootstrap prompt.

## Path Mapping

Claude Code session state often depends on absolute project paths. Cross-device sync must treat path mapping as a first-class feature:

```toml
[project]
id = "my-project"
canonical_root = "${PROJECT_ROOT}"

[[devices]]
device_id = "macbook"
root = "/Users/me/code/my-project"

[[devices]]
device_id = "windows"
root = "D:/code/my-project"
```

Handoff mode should always render portable paths. Native mode can attempt path slug remapping later.

## Excluded Data

The adapter must not export credentials, OAuth data, API keys, private MCP server secrets, or large attachments by default.

## Profiles

Suggested profiles:

```text
minimal: handoff + recent turns + patch
project: minimal + CLAUDE.md + project memory
native: project + native JSONL transcript
full: native + settings/skills/rules, requiring explicit confirmation and encryption
```
