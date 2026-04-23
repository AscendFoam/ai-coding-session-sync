# Sync Protocol Draft

This document defines the first project-bound handoff protocol for AI Coding Session Sync.

## Protocol Goals

- Keep the stable sync unit independent from Codex or Claude Code internals.
- Make exported context readable by both humans and AI assistants.
- Avoid authentication data by design.
- Preserve enough Git state to detect unsafe imports.
- Keep snapshots immutable so concurrent exports do not overwrite each other.

## Snapshot Layout

```text
.ai-session-sync/
  config.toml
  manifests/
    <snapshot_id>.json
  handoffs/
    <snapshot_id>.md
  excerpts/
    <snapshot_id>.jsonl
  patches/
    <snapshot_id>.patch
  latest/
    codex.json
    claude.json
    all.json
```

## Snapshot ID

Snapshot ids should be sortable and device-aware:

```text
YYYYMMDDTHHMMSSZ-<device_id>-<tool>
```

Example:

```text
20260423T151230Z-macbook-pro-codex
```

## Manifest

The manifest is the authoritative index for one snapshot.

Required fields:

- `schema_version`
- `snapshot_id`
- `created_at`
- `project`
- `source`
- `artifacts`
- `redaction`
- `compatibility`

The schema is intentionally conservative in the first version. Adapter-specific data should go under `source.extra` or a future `native` section, not in top-level fields.

## Handoff

The handoff Markdown file is the primary import artifact. It should include:

- current goal;
- project state;
- completed work;
- important decisions;
- relevant files;
- open questions;
- next steps;
- constraints;
- verification state.

## Excerpts

Conversation excerpts are JSONL records:

```json
{"role":"user","created_at":"2026-04-23T15:01:00+08:00","text":"..."}
```

Only cleaned, high-value excerpts should be exported. Raw transcripts belong to future native/experimental mode.

## Patch

Patch export is optional. Import must default to check-only behavior and should never mutate a dirty worktree without explicit user confirmation.
