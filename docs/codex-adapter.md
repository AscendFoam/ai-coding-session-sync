# Codex Adapter Plan

The Codex adapter extracts project-relevant context from local Codex state and converts it into the protocol defined in [`protocol.md`](./protocol.md).

## First Version

The first version should avoid native resume assumptions. It should:

- detect `CODEX_HOME`;
- fall back to `~/.codex`;
- scan likely session/transcript locations;
- rank candidate sessions by current repository path and modification time;
- extract cleaned user and assistant text;
- remove long tool output;
- normalize absolute paths to `${PROJECT_ROOT}`;
- generate a Codex-specific bootstrap prompt.

## Excluded Data

The adapter must not read or export:

- `auth.json`;
- OAuth refresh tokens;
- provider API keys;
- global credentials;
- cache/index artifacts;
- unrelated project sessions.

## Import

The import path should generate a prompt for a fresh Codex session. Launch automation can be added later, but the stable MVP should work by printing or writing the prompt.

## Native Mode

Native Codex session file sync should be experimental. If it fails, the CLI must fall back to handoff mode.
