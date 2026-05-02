# Desktop Example Fixtures

This directory contains synthetic, public-safe fixture payloads for the first desktop-oriented UI layer.

These files build on the lower-level sync-state examples under [`../public-sync-state/`](../public-sync-state/README.md), but reshape them into catalog and detail payloads that are easier for:

- `catalog.py`
- `api.py`
- a future `apps/web/` frontend
- desktop contract tests

Included fixtures:

- `sample-session-catalog.json`
- `sample-session-detail-codex.json`
- `sample-session-detail-claude.json`
- `sample-session-detail-conflict.json`
- `sample-project-catalog.json`
- `sample-desktop-ui-bundle.json`

Fixture intent:

- `sample-session-catalog.json`: session-library list payload with project summaries
- `sample-session-detail-codex.json`: clean codex detail state
- `sample-session-detail-claude.json`: dirty / patch / warning detail state
- `sample-session-detail-conflict.json`: latest-conflict + patch replay detail state
- `sample-project-catalog.json`: project-centric session grouping payload
- `sample-desktop-ui-bundle.json`: single-request desktop bootstrap payload

These fixtures are validated by:

- [`tests/test_desktop_schema_contracts.py`](../../../tests/test_desktop_schema_contracts.py)

They should stay synthetic and public-safe. Do not copy live session data into this directory.
