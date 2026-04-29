# Public Sync State Examples

This directory is the only approved home for checked-in sync-state examples in the public repository.

## Policy

- Do not commit live files copied from `.ai-session-sync/`.
- Examples must be synthetic or fully hand-redacted.
- Do not include real device ids, account identifiers, transcript paths, home directories, or private repository URLs.
- Do not include real patch payloads from unpublished work.
- Prefer `${PROJECT_ROOT}` or clearly fake sample paths over machine-local absolute paths.
- Use obviously fake identifiers such as `sample-macbook`, `session-sample-001`, and `https://example.com/org/sample.git`.

## Intended Use

Use this directory for:

- documentation examples;
- Web UI fixture payloads;
- schema compatibility samples;
- screenshots or demos that need stable input data.

If test-only fixtures are needed later, prefer `tests/fixtures/` over `.ai-session-sync/`.

## Included Fixtures

- `sample-manifest.json`
- `sample-inspect-output.json`
- `sample-latest-pointer.json`
- `sample-latest-conflict.json`
- `sample-handoff.md`
- `sample-handoff-conflict.md`
- `sample-handoff-dirty.md`
- `frontend-consumption.md`
- `sample-manifest-dirty.json`
- `sample-manifest-conflict-selected.json`
- `sample-manifest-dirty-selected.json`
- `sample-inspect-output-dirty.json`
- `sample-inspect-output-conflict-selected.json`
- `sample-inspect-output-dirty-selected.json`
- `sample-ui-bundle.json`
- `sample-ui-bundle-dirty.json`
- `sample-ui-bundle-conflict.json`
- `conflict-prototype.html`
- `conflict-prototype.css`
- `conflict-prototype.js`

These files are intentionally public-safe, schema-shaped, and stable enough for early Web UI development.

`sample-ui-bundle.json` intentionally duplicates the clean `latest` + `manifest` + `inspect` + `handoff` sample set into one payload so a prototype page can boot from a single request.

`sample-ui-bundle-dirty.json` does the same for caution-state UI work, including a dirty worktree, patch artifact, warning list, and multiple ranked source contexts.

`sample-ui-bundle-conflict.json` combines an unresolved `latest` selection state with a recommended candidate, embedded candidate detail, and patch replay guidance so a UI can prototype both the picker and the doctor panel from one payload.

`sample-handoff-conflict.md` mirrors the embedded conflict handoff markdown so split-file consumers can prototype the same operator-facing narrative without first parsing a bundle.

`sample-handoff-dirty.md` mirrors the embedded dirty-state handoff markdown so split-file consumers can prototype the same caution-state operator narrative.

`sample-manifest-conflict-selected.json` and `sample-inspect-output-conflict-selected.json` mirror the recommended candidate detail currently embedded in `sample-ui-bundle-conflict.json`, so multi-file UI prototypes can render the same conflict-state detail pane without depending on the aggregate bundle.

`sample-manifest-dirty-selected.json` and `sample-inspect-output-dirty-selected.json` mirror the selected dirty-state detail currently embedded in `sample-ui-bundle-dirty.json`, so multi-file UI prototypes can render the same warning-heavy state without depending on the aggregate bundle.

`conflict-prototype.html` is a minimal static Web UI that can load either the aggregate conflict bundle or the split-file conflict fixture set from the same page.

## Bundle vs Split Provenance

To keep this README aligned with [`frontend-consumption.md`](./frontend-consumption.md) and [`../../protocol.md`](../../protocol.md), use the same three provenance terms when discussing fixture behavior:

- `source-of-truth`
- `derived`
- `missing`

In this fixture set:

- `source-of-truth` means the value is present directly in a checked-in JSON or Markdown fixture and should be treated as contract data;
- `derived` means the value is synthesized by a frontend or prototype shell to normalize bundle-mode and split-file rendering;
- `missing` means the aggregate is intentionally absent and should stay visible as absent instead of being silently reconstructed.

Recommended rule of thumb:

- bundle fixtures such as `sample-ui-bundle.json`, `sample-ui-bundle-dirty.json`, and `sample-ui-bundle-conflict.json` may carry convenience aggregates like `latest_selection`, `handoff.summary`, and `patch_replay` as `source-of-truth`;
- split fixtures keep `manifest`, `inspect`, `latest`, and handoff markdown as `source-of-truth`, but any synthesized `latest_selection` or `handoff.summary` should be treated as `derived`;
- split mode currently leaves `patch_replay` as `missing` on purpose, so UI consumers can keep backend contract data separate from frontend convenience joins.

Practical reading guide:

- use bundle fixtures when you want a one-request bootstrap payload with embedded aggregates;
- use split fixtures when you want each contract artifact loaded independently and any normalization layer kept explicit.

## Prototype

Serve the repository root locally, then open:

- `docs/examples/public-sync-state/conflict-prototype.html?scenario=conflict&mode=bundle`
- `docs/examples/public-sync-state/conflict-prototype.html?scenario=conflict&mode=split`
- `docs/examples/public-sync-state/conflict-prototype.html?scenario=dirty&mode=bundle`
- `docs/examples/public-sync-state/conflict-prototype.html?scenario=dirty&mode=split`

Because the page uses `fetch()` to load local JSON and markdown fixtures, it should be opened through a local HTTP server instead of `file://`.
