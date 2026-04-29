# Session Handoff

## Current Goal

Resolve latest selection and review patch replay guidance in one UI flow.

## Project State

- Tool: codex
- Repository: https://example.com/org/sample-project.git
- Branch: feature/import-safety
- HEAD: fedcba9
- Dirty worktree: False
- Patch: patches/20260425T081500Z-sample-windows-codex.patch

## Completed Work

- Prepared a synthetic latest-selection conflict with two candidate snapshots.
- Added a combined UI bundle that still includes patch replay guidance for the recommended snapshot.
- Kept candidate provenance and compare timeline data in the same payload.

## Recent Context Summary

- Latest selected user request: Resolve latest selection and review patch replay guidance in one UI flow.
- Latest selected assistant update: The doctor panel should still surface patch replay recommendation even before selection is resolved.

## Important Decisions

- Keep `latest_selection` as structured UI data instead of making the frontend parse the latest pointer object directly.
- Recommend the newer Windows snapshot while still exposing the older Mac candidate.
- Keep patch replay guidance visible even when latest selection is unresolved.

## Relevant Files

- `docs/examples/public-sync-state/sample-latest-conflict.json`: standalone latest conflict fixture.
- `docs/examples/public-sync-state/sample-ui-bundle-conflict.json`: combined latest conflict and patch replay bundle.
- `docs/schemas/ui-bundle.schema.json`: UI bundle contract.
- `tests/test_schema_contracts.py`: embedded schema and consistency checks.

## Open Questions

- Should the UI block the replay panel until selection is confirmed, or show a preview recommendation immediately?
- Should the picker default to the recommended snapshot or stay fully neutral?
- Should the compare view switch candidates inline from the same page?

## Next Steps

1. Render a latest-selection picker from `latest_selection`.
2. Show recommendation reasoning near the suggested snapshot.
3. Render the patch replay panel from `patch_replay` below the picker.
4. Keep inspect candidate comparison visible so the operator can justify the choice.

## Constraints

- Do not treat the recommended snapshot as auto-resolved; the conflict still needs an explicit operator choice.
- Do not hide lower-ranked candidates.
- Do not require multi-file loading before the UI can render this dual-state prototype.

## Verification

- Embedded latest conflict matches the latest-pointer schema.
- Embedded manifest matches the manifest schema.
- Embedded inspect output matches the inspect schema.
- `latest_selection` and `patch_replay` are intentionally redundant UI aggregates.
