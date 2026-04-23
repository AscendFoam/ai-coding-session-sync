"""Command line interface for AI Coding Session Sync."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from . import __version__
from .handoff import render_excerpts, render_handoff, render_import_prompt
from .project import default_project_id, device_id, find_project_root, git_info, run_git
from .redaction import redact_text
from .schema import CONFIG_TEMPLATE, DEFAULT_TOOL, SCHEMA_VERSION, SUPPORTED_TOOLS, SYNC_DIR


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="aiss", description="Project-bound AI coding session handoff and sync.")
    parser.add_argument("--version", action="version", version=f"aiss {__version__}")
    subcommands = parser.add_subparsers(required=True)

    init_parser = subcommands.add_parser("init", help="Initialize project-local sync config.")
    init_parser.add_argument("--tool", choices=SUPPORTED_TOOLS, default=DEFAULT_TOOL)
    init_parser.add_argument("--force", action="store_true", help="Overwrite existing config.toml.")
    init_parser.set_defaults(func=cmd_init)

    status_parser = subcommands.add_parser("status", help="Show project and sync status.")
    status_parser.set_defaults(func=cmd_status)

    export_parser = subcommands.add_parser("export", help="Export a handoff snapshot.")
    export_parser.add_argument("--tool", choices=SUPPORTED_TOOLS, default=DEFAULT_TOOL)
    export_parser.add_argument("--goal", default="", help="Current goal to place in handoff.md.")
    export_parser.add_argument("--notes", default="", help="Additional notes to include in handoff.md.")
    export_parser.add_argument("--include-patch", action="store_true", help="Export git diff as a patch when available.")
    export_parser.set_defaults(func=cmd_export)

    import_parser = subcommands.add_parser("import", help="Render an import bootstrap prompt.")
    import_parser.add_argument("--tool", choices=SUPPORTED_TOOLS, default=DEFAULT_TOOL)
    import_parser.add_argument("--snapshot", default="latest", help="Snapshot id, manifest path, or 'latest'.")
    import_parser.add_argument("--print-prompt", action="store_true", help="Print prompt to stdout.")
    import_parser.add_argument("--write-prompt", help="Write prompt to a file.")
    import_parser.set_defaults(func=cmd_import)

    return parser


def cmd_init(args: argparse.Namespace) -> int:
    root = find_project_root(Path.cwd())
    sync_root = root / SYNC_DIR
    sync_root.mkdir(exist_ok=True)
    for dirname in ("manifests", "handoffs", "excerpts", "patches", "latest", "tmp", "locks"):
        (sync_root / dirname).mkdir(exist_ok=True)

    config_path = sync_root / "config.toml"
    if config_path.exists() and not args.force:
        print(f"Config already exists: {config_path}")
    else:
        project_id = default_project_id(root)
        config_path.write_text(CONFIG_TEMPLATE.format(project_id=project_id), encoding="utf-8")
        print(f"Wrote {config_path}")

    local_path = sync_root / "local.toml"
    if not local_path.exists():
        local_path.write_text(
            f'device_id = "{device_id()}"\nproject_root = "{root.as_posix()}"\n',
            encoding="utf-8",
        )
        print(f"Wrote {local_path}")

    print("Initialized AI session sync directories.")
    return 0


def cmd_status(_: argparse.Namespace) -> int:
    root = find_project_root(Path.cwd())
    sync_root = root / SYNC_DIR
    info = git_info(root)
    print(f"Project root: {root}")
    print(f"Sync dir: {sync_root} ({'present' if sync_root.exists() else 'missing'})")
    print(f"Git repo: {info['is_git_repo']}")
    print(f"Remote: {info['git_remote'] or '(none)'}")
    print(f"Branch: {info['branch'] or '(unknown)'}")
    print(f"HEAD: {info['head'] or '(unknown)'}")
    print(f"Dirty: {info['dirty']}")
    print(f"Device: {device_id()}")
    return 0


def cmd_export(args: argparse.Namespace) -> int:
    root = find_project_root(Path.cwd())
    ensure_initialized(root)
    sync_root = root / SYNC_DIR
    now = datetime.now(timezone.utc)
    created_at = now.isoformat()
    snapshot_id = f"{now.strftime('%Y%m%dT%H%M%SZ')}-{device_id()}-{args.tool}"
    info = git_info(root)

    patch_rel: str | None = None
    if args.include_patch and info["is_git_repo"] and info["dirty"]:
        code, patch, err = run_git(["diff", "--binary"], root)
        if code != 0:
            print(f"Warning: could not export patch: {err}", file=sys.stderr)
        elif patch:
            patch_rel = f"patches/{snapshot_id}.patch"
            (sync_root / patch_rel).write_text(redact_text(patch), encoding="utf-8")

    handoff_rel = f"handoffs/{snapshot_id}.md"
    excerpts_rel = f"excerpts/{snapshot_id}.jsonl"
    handoff = render_handoff(
        goal=redact_text(args.goal),
        project=info,
        tool=args.tool,
        notes=redact_text(args.notes),
        patch_path=patch_rel,
    )
    excerpts = render_excerpts(goal=redact_text(args.goal), notes=redact_text(args.notes), created_at=created_at)
    (sync_root / handoff_rel).write_text(handoff, encoding="utf-8")
    (sync_root / excerpts_rel).write_text(excerpts, encoding="utf-8")

    manifest = {
        "schema_version": SCHEMA_VERSION,
        "snapshot_id": snapshot_id,
        "created_at": created_at,
        "project": {
            "id": default_project_id(root),
            "root_hint": ".",
            "git_remote": info["git_remote"],
            "branch": info["branch"],
            "head": info["head"],
            "dirty": info["dirty"],
        },
        "source": {
            "tool": args.tool,
            "tool_version": "unknown",
            "provider_profile": "local",
            "device_id": device_id(),
        },
        "artifacts": {
            "handoff": handoff_rel,
            "recent_turns": excerpts_rel,
            "patch": patch_rel,
            "native": [],
        },
        "redaction": {
            "enabled": True,
            "ruleset": "default",
            "warnings": [],
        },
        "compatibility": {
            "import_strategy": "handoff",
            "native_resume_supported": "unknown",
        },
    }
    manifest_rel = f"manifests/{snapshot_id}.json"
    (sync_root / manifest_rel).write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    latest_path = sync_root / "latest" / f"{args.tool}.json"
    latest_path.write_text(json.dumps({"snapshot_id": snapshot_id, "manifest": manifest_rel}, indent=2) + "\n", encoding="utf-8")
    if args.tool != "all":
        (sync_root / "latest" / "all.json").write_text(
            json.dumps({"snapshot_id": snapshot_id, "manifest": manifest_rel}, indent=2) + "\n",
            encoding="utf-8",
        )

    print(f"Exported snapshot: {snapshot_id}")
    print(f"Handoff: {sync_root / handoff_rel}")
    if patch_rel:
        print(f"Patch: {sync_root / patch_rel}")
    return 0


def cmd_import(args: argparse.Namespace) -> int:
    root = find_project_root(Path.cwd())
    sync_root = root / SYNC_DIR
    manifest_path = resolve_manifest(sync_root, args.tool, args.snapshot)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    artifacts = manifest["artifacts"]
    handoff_path = sync_root / artifacts["handoff"]
    excerpts_path = sync_root / artifacts["recent_turns"] if artifacts.get("recent_turns") else None
    prompt = render_import_prompt(handoff_path, excerpts_path)

    if args.write_prompt:
        output = Path(args.write_prompt)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(prompt, encoding="utf-8")
        print(f"Wrote prompt: {output}")

    if args.print_prompt or not args.write_prompt:
        print(prompt)
    return 0


def ensure_initialized(root: Path) -> None:
    sync_root = root / SYNC_DIR
    if not (sync_root / "config.toml").exists():
        class Args:
            force = False
            tool = DEFAULT_TOOL

        cmd_init(Args())


def resolve_manifest(sync_root: Path, tool: str, snapshot: str) -> Path:
    if snapshot == "latest":
        latest_path = sync_root / "latest" / f"{tool}.json"
        if not latest_path.exists() and tool != "all":
            latest_path = sync_root / "latest" / "all.json"
        if not latest_path.exists():
            raise SystemExit(f"No latest snapshot found for tool '{tool}'.")
        latest = json.loads(latest_path.read_text(encoding="utf-8"))
        return sync_root / latest["manifest"]

    candidate = Path(snapshot)
    if candidate.exists():
        return candidate
    manifest_path = sync_root / "manifests" / f"{snapshot}.json"
    if manifest_path.exists():
        return manifest_path
    raise SystemExit(f"Snapshot not found: {snapshot}")
