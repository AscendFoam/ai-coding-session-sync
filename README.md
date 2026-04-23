# AI Coding Session Sync

Sync project-bound AI coding context across devices, accounts, and providers.

This project is an early-stage open-source tool for moving AI coding context between machines. It is designed for workflows where the same repository is edited on multiple devices, while Codex or Claude Code may use different accounts, providers, or proxy endpoints on each device.

The default strategy is **handoff-first**:

```text
local Codex / Claude Code context
        -> normalized project handoff bundle
        -> Git / local folder / future cloud backend
        -> bootstrap prompt on another machine
```

Native transcript/session sync can be added as an experimental feature later, but it should never be the only path.

## Why

Codex and Claude Code sessions are primarily local state. In real cross-device workflows, native resume can be fragile because of absolute paths, account differences, provider differences, local caches, and changing internal file formats.

AI Coding Session Sync treats the stable unit as a **project-bound context package**:

- what the current goal is;
- what has already been done;
- which files matter;
- which decisions were made;
- what remains risky or unfinished;
- what patch represents uncommitted work.

That package can be reviewed, redacted, encrypted, versioned, and imported by a new session on another machine.

## Quick Start

Run from a project directory:

```bash
PYTHONPATH=src python -m aiss init --tool all
PYTHONPATH=src python -m aiss export --tool codex --goal "Continue the current feature" --include-patch
PYTHONPATH=src python -m aiss import --tool codex --print-prompt
```

The CLI command name planned for packaged releases is:

```bash
aiss
```

## Current State

This repository currently contains:

- a detailed engineering plan in [`docs/工程化项目推进方案.md`](docs/工程化项目推进方案.md);
- a minimal standard-library Python CLI skeleton;
- protocol and security documentation;
- smoke tests for the first CLI surface.

Implemented now:

- `init`
- `status`
- `export`
- `import --print-prompt`
- manifest generation
- handoff generation
- optional Git patch export

Run the current smoke test suite with:

```bash
PYTHONPATH=src python -m unittest -v
```

Not implemented yet:

- Codex native transcript parsing;
- Claude Code native JSONL parsing;
- remote Git push/pull backend;
- encryption;
- native resume/path remap.

## Safety

Do not sync authentication files. Do not publish raw transcripts unless you understand the risk. AI coding sessions may include source code, command output, logs, paths, and secrets.

The project should default to:

- no auth sync;
- minimal handoff sync;
- redaction before write;
- sidecar storage for sensitive work;
- encryption before remote sync.

## License

MIT.
