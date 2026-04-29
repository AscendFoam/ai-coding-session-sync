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

## Draft Schemas

To make the protocol directly consumable by future Web UI or validation tooling, this draft also ships machine-readable JSON Schema files:

- [`schemas/manifest.schema.json`](./schemas/manifest.schema.json): exported snapshot manifest
- [`schemas/inspect-output.schema.json`](./schemas/inspect-output.schema.json): `aiss inspect --json` output
- [`schemas/latest-pointer.schema.json`](./schemas/latest-pointer.schema.json): `latest/*.json` snapshot pointer files

Current draft policy:

- target: JSON Schema draft 2020-12
- schema version alignment: `0.1.0`
- compatibility goal: additive changes should remain backward compatible for UI consumers
- stability scope: field names documented in these schema files should be treated as the canonical draft contract

## Consumer Provenance Terms

To keep protocol discussions aligned with frontend consumption, this draft also uses three provenance terms for contract interpretation:

- `source-of-truth`
- `derived`
- `missing`

These terms describe how a consumer should treat a value after loading one or more protocol artifacts. They are consumer semantics, not current schema fields.

Definitions:

- `source-of-truth`: the value is present directly in a checked-in artifact or payload and should be treated as contract data.
- `derived`: the value is synthesized by the consumer to normalize bundle-mode and split-file rendering, but it is not yet guaranteed as backend contract data.
- `missing`: the aggregate is intentionally absent from the loaded artifacts, and the consumer should surface that absence instead of silently inventing it.

Recommended rule of thumb:

- treat `manifest`, `inspect`, `latest`, `handoff.markdown`, and bundle-provided `patch_replay` as `source-of-truth`;
- treat split-mode convenience joins such as synthesized `latest_selection` or synthesized `handoff.summary` as `derived`;
- treat intentionally absent aggregates, such as split-mode `patch_replay`, as `missing`.

Current scope note:

- these terms help consumers, docs, and prototype UIs talk about the same payloads with the same vocabulary;
- they do not currently appear as required fields in `manifest.schema.json`, `inspect-output.schema.json`, or `latest-pointer.schema.json`;
- future backend payloads may promote some currently `derived` values into `source-of-truth` fields.

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

For machine-readable validation, use [`schemas/manifest.schema.json`](./schemas/manifest.schema.json).

Current stable implementations also attach session selection metadata under `source.contexts[]` so one snapshot can explain why a local session was selected. Recommended fields include:

- `tool`
- `source_kind`
- `session_id`
- `title`
- `updated_at`
- `transcript_path`
- `excerpt_count`
- `total_excerpt_count`
- `total_user_count`
- `total_assistant_count`
- `score`
- `score_reasons`
- `goal_candidate`

Example:

```json
{
  "source": {
    "tool": "codex",
    "tool_version": "unknown",
    "provider_profile": "local",
    "device_id": "macbook-pro",
    "contexts": [
      {
        "tool": "codex",
        "source_kind": "transcript",
        "session_id": "session-123",
        "title": "Implement export transcript extraction",
        "updated_at": "2026-04-25T06:00:00Z",
        "transcript_path": "/Users/me/.codex/sessions/.../rollout.jsonl",
        "excerpt_count": 10,
        "total_excerpt_count": 63,
        "total_user_count": 7,
        "total_assistant_count": 56,
        "score": 276,
        "score_reasons": [
          "cwd exactly matches project root",
          "7 user excerpt(s)",
          "56 assistant excerpt(s)",
          "goal candidate available"
        ],
        "goal_candidate": "Continue improving inspect compare output."
      }
    ]
  }
}
```

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

## Inspect JSON Compare Metadata

`aiss inspect --json` exposes richer compare metadata than the exported `recent_turns.jsonl`. This inspect payload is intended for debugging, visualization, and future Web UI consumers.

For machine-readable validation, use [`schemas/inspect-output.schema.json`](./schemas/inspect-output.schema.json).

`all_excerpts[]` represents the full cleaned excerpt sequence before representative-window trimming:

```json
{
  "role": "assistant",
  "created_at": "2026-04-25T07:06:30.721Z",
  "text": "...",
  "selected": true,
  "selected_index": 2
}
```

Field rules:

- `selected`: whether this excerpt survived representative-window selection
- `selected_index`: 1-based index in `excerpts[]`; `null` when trimmed out

`excerpts[]` represents the selected representative window:

```json
{
  "role": "assistant",
  "created_at": "2026-04-25T07:06:30.721Z",
  "text": "...",
  "selected_index": 2,
  "all_excerpt_index": 75
}
```

Field rules:

- `selected_index`: 1-based index inside `excerpts[]`
- `all_excerpt_index`: 1-based index of the same item inside `all_excerpts[]`

Together, these fields support bidirectional navigation:

- `all_excerpts[*].selected_index` lets UI jump from the full list to the selected list
- `excerpts[*].all_excerpt_index` lets UI jump back from the selected list to the full list

Recommended UI usage:

- render `all_excerpts[]` as the full timeline
- render `excerpts[]` as the selected summary window
- use `selected_index` and `all_excerpt_index` as stable join keys instead of re-matching by text
- treat `score`, `score_reasons`, and `goal_candidate` as explainability fields for candidate ranking

## Patch

Patch export is optional. Import must default to check-only behavior and should never mutate a dirty worktree without explicit user confirmation.

Current import contract:

- `aiss import` without `--apply-patch` only inspects and explains patch replay risk.
- The inspection summary should include:
  - whether the patch artifact exists locally;
  - whether the current checkout is a Git worktree;
  - current branch and HEAD;
  - export-time branch and HEAD from the manifest;
  - whether plain `git apply --check` succeeds;
  - whether `git apply --3way --check` succeeds.
- Dirty worktrees must be refused by default for any mutating patch replay command.
- `--allow-dirty` is an explicit escape hatch for advanced cases and should remain opt-in.

Recommended replay strategies:

- `apply`: plain `git apply`; use when `git apply --check` is already clean.
- `3way`: `git apply --3way`; use when plain apply no longer fits but Git can still merge against blob history.
- `branch`: create a temporary branch and replay there, typically with plain apply when possible and `--3way` as fallback.

Current CLI mapping:

```bash
aiss import --tool codex --snapshot latest
aiss import --tool codex --snapshot latest --apply-patch
aiss import --tool codex --snapshot latest --apply-patch --patch-mode 3way
aiss import --tool codex --snapshot latest --apply-patch --patch-mode branch
```

Safety intent:

- default path: inspect only;
- fast path: direct apply on a clean worktree;
- resilient path: 3-way replay when the checkout has drifted;
- safer isolation path: temporary branch replay when the operator wants conflict resolution away from the current checkout.
