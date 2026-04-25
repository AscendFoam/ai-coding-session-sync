# Session Handoff

## Current Goal

Continue implementing inspect compare metadata for the Web UI.

## Project State

- Tool: codex
- Repository: https://example.com/org/sample-project.git
- Branch: main
- HEAD: abc1234
- Dirty worktree: False
- Patch: (not exported)

## Completed Work

- Added compare metadata to `inspect --json` so `all_excerpts` exposes `selected` and `selected_index`.
- Added reverse mapping in `excerpts` using `all_excerpt_index` for direct UI linking.
- Split schema validation into a dedicated contract test layer.

## Recent Context Summary

- Latest user request: Continue implementing inspect compare metadata for the Web UI.
- Latest selected assistant update: I am validating the compare payload shape against the schema draft.

## Important Decisions

- Keep exported `recent_turns.jsonl` lightweight and reserve compare metadata for `inspect --json`.
- Treat schema files as the canonical draft contract for Web UI consumers.
- Keep public examples synthetic and safe for a public repository.

## Relevant Files

- `src/aiss/cli.py`: inspect output formatting and JSON payload shape.
- `docs/schemas/inspect-output.schema.json`: schema contract for inspect payloads.
- `tests/test_schema_contracts.py`: contract tests for export, inspect, and public fixtures.
- `docs/examples/public-sync-state/`: public-safe fixture pack for UI development.

## Open Questions

- Should the first Web UI open on latest snapshot summary or inspect compare mode?
- Should compare view support collapsing trimmed excerpts by default?
- Do we want a second fixture with `dirty: true` and a patch artifact for UI states?

## Next Steps

1. Build a snapshot summary view from `sample-manifest.json`.
2. Build a compare timeline from `sample-inspect-output.json`.
3. Add a handoff reader pane using `sample-handoff.md`.
4. Wire latest pointer loading using both normal and conflict examples.

## Constraints

- Do not assume native resume support.
- Do not expose auth files, real transcript paths, or live machine identifiers.
- Do not require Web UI consumers to reconstruct compare indexes by matching text.

## Verification

- `inspect --json` matches schema.
- compare indexes are consistent across `all_excerpts` and `excerpts`.
- public fixtures are validated in `tests/test_schema_contracts.py`.
