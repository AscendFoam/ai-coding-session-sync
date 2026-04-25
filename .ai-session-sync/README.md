# Runtime Sync State

This public repository does not track live `.ai-session-sync/` runtime data.

Ignored by default:

- `manifests/`
- `handoffs/`
- `excerpts/`
- `patches/`
- `latest/`
- `native/`
- `local.toml`
- `tmp/`
- `locks/`

Why:

- real session exports can contain private prompts, local paths, device ids, repository metadata, and partial source context;
- public source repos should not accumulate live handoff artifacts from real machines.

Public examples belong under `docs/examples/public-sync-state/`, using synthetic or fully redacted data only.
