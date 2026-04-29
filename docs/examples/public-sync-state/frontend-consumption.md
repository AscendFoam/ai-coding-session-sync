# Frontend Consumption Notes

This page explains how to map the public fixture set into a first-pass Web UI.

## Fixture Set

- `sample-ui-bundle.json`
- `sample-ui-bundle-dirty.json`
- `sample-ui-bundle-conflict.json`
- `sample-latest-pointer.json`
- `sample-latest-conflict.json`
- `sample-manifest.json`
- `sample-manifest-conflict-selected.json`
- `sample-manifest-dirty-selected.json`
- `sample-inspect-output.json`
- `sample-inspect-output-conflict-selected.json`
- `sample-inspect-output-dirty-selected.json`
- `sample-handoff.md`
- `sample-handoff-conflict.md`
- `sample-handoff-dirty.md`

These files are synthetic, public-safe, and intended for early UI work before a live backend exists.

If you want a ready-made prototype shell instead of wiring the first page from scratch, open `conflict-prototype.html` from a local HTTP server and switch between:

- `?scenario=conflict&mode=bundle`
- `?scenario=conflict&mode=split`
- `?scenario=dirty&mode=bundle`
- `?scenario=dirty&mode=split`

## Fastest Path

For a single-request prototype, start with:

- `sample-ui-bundle.json`
- `sample-ui-bundle-dirty.json`
- `sample-ui-bundle-conflict.json`

It already inlines:

- `latest`
- `latest_selection`
- `manifest`
- `inspect`
- `handoff`
- `patch_replay`

Use the split fixtures when you want to test conflict state, dirty state, or individual contract files in isolation.

## Field Provenance Rules

When the frontend consumes these fixtures, distinguish between two classes of values:

- `source-of-truth`
- `derived`

`source-of-truth` means the value is provided directly by a checked-in fixture or bundle payload and should be treated as backend contract data.

`derived` means the value is synthesized by the frontend or prototype shell to keep a uniform view model across bundle and split-file paths. Derived values are useful for rendering, but they should not be mistaken for fields that already exist in the backend contract.

Recommended rule of thumb:

- treat `manifest`, `inspect`, `latest`, `handoff.markdown`, and bundle-provided `patch_replay` as `source-of-truth`;
- treat split-mode convenience joins such as synthesized `latest_selection` or synthesized `handoff.summary` as `derived`;
- treat intentionally absent aggregates, such as split-mode `patch_replay`, as `missing` rather than silently reconstructing them from prose.

Current prototype alignment:

- bundle mode usually keeps `latest_selection`, `handoff.summary`, and `patch_replay` as `source-of-truth`;
- split mode may expose `latest_selection` and `handoff.summary` as `derived` convenience fields so the UI can keep a stable render shape;
- split mode currently leaves `patch_replay` missing on purpose, so the difference between backend contract data and frontend convenience data stays visible.

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
- `sample-ui-bundle-conflict.json`

Use it to model a selection modal or picker:

- `candidates[]` -> selectable snapshot list
- `requires_selection` -> blocking state before opening a snapshot

If you use the bundled conflict fixture, prefer `latest_selection` for direct UI rendering:

- `latest_selection.state` -> resolved vs picker-required state
- `latest_selection.candidates[]` -> candidate list in stable display order
- `latest_selection.recommended_snapshot_id` -> highlighted recommendation
- `latest_selection.recommended_reason` -> helper copy beside the recommendation

Important contract note:

- when `latest_selection.state == "requires-selection"`, `entry.snapshot_id` is the snapshot whose `manifest` / `inspect` / `handoff` data is embedded in the bundle, not a globally confirmed latest selection.
- in the current public conflict bundle, that embedded snapshot is also the recommended candidate so the UI can render a useful default detail pane immediately.

### 2. Latest Selection + Replay Combined View

Primary input:

- `sample-ui-bundle-conflict.json`

Use this bundle when you want one payload that drives both:

- a latest-selection picker; and
- a patch replay recommendation panel for the recommended candidate.

Recommended mapping:

- picker state:
  - `latest_selection.state`
  - `latest_selection.candidates`
  - `latest_selection.recommended_snapshot_id`
  - `latest_selection.recommended_reason`
- candidate detail pane:
  - `manifest`
  - `inspect.codex[0]`
  - `handoff`
- replay guidance:
  - `patch_replay`

Suggested UI behavior:

- keep the picker unresolved until the operator makes a choice;
- still render the recommended candidate detail pane immediately from the embedded `manifest` and `inspect`;
- place `patch_replay` below or beside the picker so replay risk is visible before import begins.

If you are prototyping in split-file mode, pair:

- `sample-latest-conflict.json`
- `sample-manifest-conflict-selected.json`
- `sample-inspect-output-conflict-selected.json`
- `sample-handoff-conflict.md`

This gives the multi-file UI the same currently selected detail pane that is embedded in `sample-ui-bundle-conflict.json`.

Important split-file note:

- `sample-manifest-conflict-selected.json` is the currently loaded candidate detail, not proof that the global latest conflict has been resolved.
- `sample-inspect-output-conflict-selected.json` still includes the lower-ranked Mac candidate so the UI can explain why the Windows snapshot is being recommended.
- when split mode exposes a unified `latest_selection` object, that object should be treated as `derived` unless a future backend payload starts emitting it directly outside the bundle path.

### 3. Snapshot Summary View

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

For the conflict flow, `sample-handoff-conflict.md` gives split-file consumers the same operator-facing narrative that is embedded inside `sample-ui-bundle-conflict.json`.

### 4. Candidate Explainability View

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

### 5. Compare Timeline View

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

### 6. Tool Tabs

Primary input:

- `sample-ui-bundle.json`
- `sample-inspect-output.json`

Use the top-level tool keys directly:

- `inspect.codex`
- `inspect.claude`

This makes it easy to build a segmented control or tabs even before a backend exists.

### 7. Dirty / Warning Variant

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

The dirty bundle handoff metadata already mirrors that recommendation flow, so the UI can use:

- `handoff.summary` for a compact human description of why branch-first replay is being recommended;
- `handoff.markdown` for the longer operator-facing handoff narrative;
- `patch_replay` for structured rendering without parsing prose.

If you want the same caution-state experience in split-file mode, pair:

- `sample-latest-pointer.json`
- `sample-manifest-dirty-selected.json`
- `sample-inspect-output-dirty-selected.json`
- `sample-handoff-dirty.md`

Important split-file note:

- `sample-manifest-dirty-selected.json` is a selected snapshot detail, not a separate latest conflict flow.
- `sample-inspect-output-dirty-selected.json` keeps the selected Claude compare timeline and its ranking metadata, but the structured `patch_replay` aggregate still only exists in bundle mode today.
- if the UI adds a short dirty-state summary in split mode, treat it as `derived`; only the bundle path currently carries `handoff.summary` and `patch_replay` as explicit convenience aggregates.

### 8. Patch Replay Recommendation View

Primary input:

- `sample-ui-bundle.json`
- `sample-ui-bundle-dirty.json`
- `sample-ui-bundle-conflict.json`

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
- allow this panel to render even while `latest_selection.state == "requires-selection"` when the bundle already embeds the recommended candidate detail;
- keep this panel independent from the handoff markdown so the UI can summarize replay risk without parsing prose.

## Minimal UI Build Order

1. Load `sample-ui-bundle.json`
2. Render latest badge or page header from `entry` and `latest`
3. Render snapshot summary from `manifest`
4. Render handoff pane from `handoff.markdown`
5. Render compare timeline from `inspect`
6. Add conflict-state handling using `sample-ui-bundle-conflict.json`
7. Use `sample-latest-conflict.json` plus `sample-manifest-conflict-selected.json`, `sample-inspect-output-conflict-selected.json`, and `sample-handoff-conflict.md` for multi-file conflict-state loading
8. Add patch replay recommendation panel using `patch_replay`
9. Add dirty / warning handling using `sample-ui-bundle-dirty.json`
10. Use `sample-latest-pointer.json` plus `sample-manifest-dirty-selected.json`, `sample-inspect-output-dirty-selected.json`, and `sample-handoff-dirty.md` for multi-file dirty-state loading
11. Keep `sample-manifest-dirty.json` and `sample-inspect-output-dirty.json` for isolated state testing

## Practical Notes

- Treat schema files under `docs/schemas/` as the contract source of truth.
- Treat fixture files under `docs/examples/public-sync-state/` as the design/dev seed data.
- Treat `docs/schemas/ui-bundle.schema.json` as the convenience contract for single-request UI bootstrap payloads.
- Keep `source-of-truth` and `derived` fields distinct in frontend state models so protocol evolution does not get hidden inside view helpers.
- Prefer index-based joins over text matching.
- Preserve unknown future fields in UI models where practical so additive protocol changes stay cheap.
