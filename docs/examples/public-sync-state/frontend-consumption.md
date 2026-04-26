# Frontend Consumption Notes

This page explains how to map the public fixture set into a first-pass Web UI.

## Fixture Set

- `sample-ui-bundle.json`
- `sample-ui-bundle-dirty.json`
- `sample-latest-pointer.json`
- `sample-latest-conflict.json`
- `sample-manifest.json`
- `sample-inspect-output.json`
- `sample-handoff.md`

These files are synthetic, public-safe, and intended for early UI work before a live backend exists.

## Fastest Path

For a single-request prototype, start with:

- `sample-ui-bundle.json`
- `sample-ui-bundle-dirty.json`

It already inlines:

- `latest`
- `manifest`
- `inspect`
- `handoff`
- `patch_replay`

Use the split fixtures when you want to test conflict state, dirty state, or individual contract files in isolation.

## Suggested Core Views

### 1. Latest Entry View

Primary input:

- `sample-ui-bundle.json`
- `sample-latest-pointer.json`

Use it to model the app entry state:

- `entry.snapshot_id` or `latest.snapshot_id` -> current selection badge or page header
- `latest.manifest` -> manifest fetch target or reference label

Conflict state:

- `sample-latest-conflict.json`

Use it to model a selection modal or picker:

- `candidates[]` -> selectable snapshot list
- `requires_selection` -> blocking state before opening a snapshot

### 2. Snapshot Summary View

Primary input:

- `sample-ui-bundle.json`
- `sample-manifest.json`
- `sample-handoff.md`

Recommended mapping:

- header:
  - `manifest.project.id`
  - `manifest.source.tool`
  - `manifest.snapshot_id`
  - `manifest.created_at`
- repo summary card:
  - `manifest.project.git_remote`
  - `manifest.project.branch`
  - `manifest.project.head`
  - `manifest.project.dirty`
- source/session card:
  - `manifest.source.device_id`
  - `manifest.source.provider_profile`
  - `manifest.source.contexts[0].title`
  - `manifest.source.contexts[0].goal_candidate`
  - `manifest.source.contexts[0].score`
- artifacts card:
  - `manifest.artifacts.handoff`
  - `manifest.artifacts.recent_turns`
  - `manifest.artifacts.patch`

Use `handoff.markdown` from the bundle as the right-side detail pane or a dedicated tab. The standalone `sample-handoff.md` remains useful when you want a raw markdown-only fixture.

### 3. Candidate Explainability View

Primary input:

- `sample-ui-bundle.json`
- `sample-manifest.json`
- `sample-inspect-output.json`

Recommended mapping:

- `manifest.source.contexts[]` for exported snapshot provenance
- `inspect.codex[]` / `inspect.claude[]` for live candidate comparison

Display:

- `title`
- `goal_candidate`
- `score`
- `score_reasons`
- excerpt counts:
  - `excerpt_count`
  - `total_excerpt_count`
  - `total_user_count`
  - `total_assistant_count`

This is the view that explains why one session won over another.

### 4. Compare Timeline View

Primary input:

- `sample-ui-bundle.json`
- `sample-inspect-output.json`

Recommended layout:

- left or top rail: `inspect.<tool>[0].excerpts[]` as the selected window
- main timeline: `inspect.<tool>[0].all_excerpts[]`

Join rules:

- `all_excerpts[*].selected_index` lets you jump from the full timeline to the selected list
- `excerpts[*].all_excerpt_index` lets you jump back from the selected list to the full timeline

Recommended UI behavior:

- highlight `all_excerpts[*].selected == true`
- dim or collapse trimmed excerpts
- show `selected_index` as an ordinal badge in both panes
- scroll the timeline to `all_excerpt_index` when a selected excerpt is clicked

### 5. Tool Tabs

Primary input:

- `sample-ui-bundle.json`
- `sample-inspect-output.json`

Use the top-level tool keys directly:

- `inspect.codex`
- `inspect.claude`

This makes it easy to build a segmented control or tabs even before a backend exists.

### 6. Dirty / Warning Variant

Primary input:

- `sample-manifest-dirty.json`
- `sample-inspect-output-dirty.json`
- `sample-ui-bundle-dirty.json`

Use this variant to test caution states:

- `project.dirty == true` should surface a dirty badge or warning banner
- `artifacts.patch` should light up a patch indicator or preview action
- `redaction.warnings[]` should render as a caution list
- `source.contexts.length > 1` should render a candidate list or expandable ranking section

Suggested UI behavior:

- show the dirty state in the snapshot header;
- show patch availability next to artifacts;
- expose redaction warnings near the summary or security panel;
- render multiple contexts as stacked candidates with score and reasoning;
- keep compare timeline behavior identical to the clean sample so the view logic stays consistent.

When you want those states in one request instead of three separate files, use `sample-ui-bundle-dirty.json` and map:

- `manifest.project.dirty`
- `manifest.artifacts.patch`
- `manifest.redaction.warnings`
- `manifest.source.contexts`
- `inspect.claude[0]`
- `patch_replay`

### 7. Patch Replay Recommendation View

Primary input:

- `sample-ui-bundle.json`
- `sample-ui-bundle-dirty.json`

Use `patch_replay` as the direct data source for a doctor/status-style guidance panel.

Recommended mapping:

- badge or state chip:
  - `patch_replay.state`
- capability rows:
  - `patch_replay.plain_apply_state`
  - `patch_replay.three_way_state`
- recommendation callout:
  - `patch_replay.recommended_mode`
  - `patch_replay.recommended_reason`
  - `patch_replay.recommended_command`
- optional artifact link:
  - `patch_replay.patch_path`

Suggested UI behavior:

- render `state == "none"` as an informational empty state rather than a warning;
- render `state == "blocked"` as a caution state that explains why replay is paused;
- render `recommended_mode == "branch"` as the strongest safe recommendation when conflicts or dirty state are present;
- expose `recommended_command` as copyable command text for terminal-oriented users;
- keep this panel independent from the handoff markdown so the UI can summarize replay risk without parsing prose.

## Minimal UI Build Order

1. Load `sample-ui-bundle.json`
2. Render latest badge or page header from `entry` and `latest`
3. Render snapshot summary from `manifest`
4. Render handoff pane from `handoff.markdown`
5. Render compare timeline from `inspect`
6. Add conflict-state handling using `sample-latest-conflict.json`
7. Add patch replay recommendation panel using `patch_replay`
8. Add dirty / warning handling using `sample-ui-bundle-dirty.json`
9. Keep `sample-manifest-dirty.json` and `sample-inspect-output-dirty.json` for isolated state testing

## Practical Notes

- Treat schema files under `docs/schemas/` as the contract source of truth.
- Treat fixture files under `docs/examples/public-sync-state/` as the design/dev seed data.
- Treat `docs/schemas/ui-bundle.schema.json` as the convenience contract for single-request UI bootstrap payloads.
- Prefer index-based joins over text matching.
- Preserve unknown future fields in UI models where practical so additive protocol changes stay cheap.
