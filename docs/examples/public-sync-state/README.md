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
- `frontend-consumption.md`
- `sample-manifest-dirty.json`
- `sample-inspect-output-dirty.json`
- `sample-ui-bundle.json`

These files are intentionally public-safe, schema-shaped, and stable enough for early Web UI development.

`sample-ui-bundle.json` intentionally duplicates the clean `latest` + `manifest` + `inspect` + `handoff` sample set into one payload so a prototype page can boot from a single request.
