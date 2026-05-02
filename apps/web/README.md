# AISS Web Prototype

This is the first desktop-oriented web workbench for AISS.

It supports two data modes from the same screen:

- `Fixtures`: loads synthetic desktop fixtures through the local AISS API
- `Live API`: loads real local session data from `aiss serve`

## Start the local API

From the repo root:

```bash
PYTHONPATH=src python -m aiss serve --host 127.0.0.1 --port 8765
```

If you want to point it at a specific project root:

```bash
PYTHONPATH=src python -m aiss serve --host 127.0.0.1 --port 8765 --project-root /path/to/project
```

## Start the web prototype

From `apps/web/`:

```bash
npm run dev
```

Then open:

```text
http://127.0.0.1:4173
```

## Current scope

- session library
- project catalog
- session detail
- manifest / patch replay / handoff panels
- selected excerpts vs full timeline
- fixture/live mode switch

This is intentionally a lightweight prototype shell. The current version uses plain HTML/CSS/JS so the data contract and UI structure can settle before a framework migration.
