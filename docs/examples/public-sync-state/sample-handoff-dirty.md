# Session Handoff

## Current Goal

Cover dirty, patch, and warning states in the Web UI.

## Project State

- Tool: claude
- Repository: https://example.com/org/sample-project.git
- Branch: feature/inspect-ui
- HEAD: def5678
- Dirty worktree: True
- Patch: patches/20260425T081500Z-sample-windows-claude.patch

## Completed Work

- Added a dirty snapshot example with a patch artifact reference.
- Added redaction warnings to exercise caution-state UI.
- Added multiple ranked source contexts so the UI can show provenance competition.
- Added patch replay guidance showing that branch-first replay is the safest recommendation here.

## Recent Context Summary

- Latest selected user request: Cover dirty, patch, and warning states in the Web UI.
- Latest selected assistant update: I am validating the dirty sample against the schema.

## Important Decisions

- Keep the dirty example synthetic even though it models a riskier project state.
- Preserve the same compare index contract as the clean sample.
- Surface warnings in both manifest metadata and the handoff summary.
- Expose patch replay recommendation as structured UI data instead of making the frontend parse markdown.

## Relevant Files

- `docs/examples/public-sync-state/sample-manifest-dirty.json`: dirty manifest fixture.
- `docs/examples/public-sync-state/sample-inspect-output-dirty.json`: dirty inspect fixture.
- `docs/examples/public-sync-state/sample-ui-bundle-dirty.json`: single-file dirty UI bootstrap payload.
- `tests/test_schema_contracts.py`: contract tests for clean and dirty bundles.

## Open Questions

- Should the UI show warnings inline in the header or only in a dedicated panel?
- Should a patch preview be collapsed by default for risky states?
- Should multiple ranked contexts be rendered as tabs, a list, or a compare drawer?
- Should patch replay guidance sit near artifacts or in a dedicated doctor panel?

## Next Steps

1. Boot the caution-state prototype directly from `sample-ui-bundle-dirty.json`.
2. Render the dirty badge and patch indicator from the manifest section.
3. Render warning chips or banners from `redaction.warnings`.
4. Show ranked contexts next to the selected compare timeline.
5. Render `patch_replay` as a doctor-style recommendation panel.

## Constraints

- Do not treat synthetic warnings as real security findings.
- Do not require the UI to load a second file before it can render the dirty state.
- Do not infer ranking by title; use the provided score and score reasons.
- Do not make the frontend infer replay strategy from prose when `patch_replay` is present.

## Verification

- Embedded manifest matches the manifest schema.
- Embedded inspect output matches the inspect schema.
- Compare indexes remain consistent across `all_excerpts` and `excerpts`.
- `patch_replay` explicitly recommends branch replay for this dirty caution state.
