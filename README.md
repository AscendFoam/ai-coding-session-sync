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
- import-time patch safety checks
- `import --apply-patch --patch-mode apply|3way|branch`
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

Patch replay follows the same conservative rule:

- `aiss import` stays check-only by default;
- the CLI surfaces patch presence, branch/HEAD drift, dirty worktree state, and `git apply --check` results;
- `--apply-patch` is always explicit;
- dirty worktrees are blocked unless you also pass `--allow-dirty`;
- `--patch-mode 3way` lets Git attempt a merge when plain apply no longer fits;
- `--patch-mode branch` replays the patch on a temporary branch so conflict resolution does not immediately land on your main checkout.

Example:

```bash
PYTHONPATH=src python -m aiss export --tool codex --include-patch
PYTHONPATH=src python -m aiss import --tool codex --snapshot latest --print-prompt

# apply directly when the check is clean
PYTHONPATH=src python -m aiss import --tool codex --snapshot latest --apply-patch

# let Git try a 3-way merge when HEAD has moved
PYTHONPATH=src python -m aiss import --tool codex --snapshot latest --apply-patch --patch-mode 3way

# safer isolation path for risky replays
PYTHONPATH=src python -m aiss import --tool codex --snapshot latest --apply-patch --patch-mode branch
```

## Public Repo Defaults

This repository is intended to remain public, so live `.ai-session-sync/` runtime state is ignored by default.

- Do not commit real `manifests/`, `handoffs/`, `excerpts/`, `patches/`, or `latest/` files from active machines.
- Keep real sync state in a private sidecar repo or another private backend.
- Put public examples under [`docs/examples/public-sync-state/`](docs/examples/public-sync-state/README.md) using synthetic or fully redacted data only.

## License

MIT.
