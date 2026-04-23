# Security Model

AI coding sessions can contain source code, logs, shell output, private paths, issue details, credentials, and partial secrets. This project must treat all exported context as sensitive unless the user explicitly decides otherwise.

## Default Denylist

The tool must never sync these files by default:

```text
~/.codex/auth.json
~/.claude credentials or OAuth data
.env
.env.*
id_rsa
id_ed25519
*.pem
*.key
cloud provider credentials
cookies
browser storage
node_modules
.venv
dist
build
```

## Redaction

The first redaction engine should cover:

- OpenAI-style keys;
- Anthropic-style keys;
- GitHub tokens;
- AWS access keys;
- common bearer tokens;
- `.env` assignments;
- local absolute path normalization.

Redaction is not a security proof. The CLI should show warnings and recommend encryption for remote sync.

## Storage Guidance

Recommended storage by project type:

```text
Personal private repo: in-repo handoff can be acceptable.
Shared private repo: sidecar repo is safer.
Public repo: avoid raw excerpts; use sidecar repo and encryption.
Sensitive work: use sidecar repo plus encryption.
```

## Native Mode

Native transcript sync is higher risk than handoff sync. It can include full conversation history and unfiltered tool output. It should remain opt-in, clearly labeled as experimental, and strongly paired with encryption.
