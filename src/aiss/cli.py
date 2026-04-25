"""Command line interface for AI Coding Session Sync."""

from __future__ import annotations

import argparse
from collections import defaultdict
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from . import __version__
from .adapters import (
    Excerpt,
    ExtractedContext,
    collect_claude_contexts,
    collect_codex_contexts,
    extract_claude_context,
    extract_codex_context,
)
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

    inspect_parser = subcommands.add_parser("inspect", help="Inspect transcript candidates and extracted excerpts.")
    inspect_parser.add_argument("--tool", choices=SUPPORTED_TOOLS, default=DEFAULT_TOOL)
    inspect_parser.add_argument("--limit", type=int, default=3, help="Number of candidate sessions to show per tool.")
    inspect_parser.add_argument(
        "--all-excerpts",
        action="store_true",
        help="Show all extracted excerpts before representative-window trimming.",
    )
    inspect_parser.add_argument(
        "--full",
        action="store_true",
        help="Do not truncate excerpt text in formatted output.",
    )
    inspect_parser.add_argument(
        "--compare",
        action="store_true",
        help="Show all excerpts with selected-vs-trimmed markers for window debugging.",
    )
    inspect_parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON instead of formatted text.",
    )
    inspect_parser.set_defaults(func=cmd_inspect)

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
    contexts = _collect_contexts(root, args.tool)
    excerpts = _collect_excerpts(contexts)

    goal = redact_text(args.goal) if args.goal else _derive_goal_from_contexts(contexts, excerpts)
    notes = _build_notes(args.notes, contexts)

    if not excerpts and goal:
        excerpts = [Excerpt(role="user", created_at=created_at, text=goal, tool=args.tool)]
    if not excerpts and notes:
        excerpts = [Excerpt(role="user", created_at=created_at, text=notes, tool=args.tool)]

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
        goal=goal,
        project=info,
        tool=args.tool,
        notes=notes,
        patch_path=patch_rel,
        contexts=contexts,
        project_root=root,
    )
    excerpt_payload = render_excerpts(excerpts)
    (sync_root / handoff_rel).write_text(handoff, encoding="utf-8")
    (sync_root / excerpts_rel).write_text(excerpt_payload, encoding="utf-8")

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
            "contexts": [
                _manifest_context_entry(context)
                for context in contexts
            ],
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
            "warnings": [warning for context in contexts for warning in context.warnings],
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


def cmd_inspect(args: argparse.Namespace) -> int:
    root = find_project_root(Path.cwd())
    candidates_by_tool = _collect_context_candidates(root, args.tool, limit=args.limit)
    if args.json:
        payload = {tool: [_context_to_dict(context) for context in contexts] for tool, contexts in candidates_by_tool.items()}
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    print(f"Project root: {root}")
    for tool, contexts in candidates_by_tool.items():
        print(f"\n[{tool}]")
        if not contexts:
            print("  No matching local transcript candidates found.")
            continue
        for index, context in enumerate(contexts, start=1):
            print(f"  Candidate {index}: {context.title or '(untitled)'}")
            print(f"    score: {context.score}")
            print(f"    reasons: {', '.join(context.score_reasons) or '(none)'}")
            print(f"    source: {context.source_kind}")
            print(f"    session: {context.session_id or '(none)'}")
            print(f"    updated: {context.updated_at or '(unknown)'}")
            print(f"    cwd: {context.cwd or '(unknown)'}")
            print(f"    transcript: {context.transcript_path.as_posix() if context.transcript_path else '(none)'}")
            print(f"    goal: {context.goal_candidate or '(none)'}")
            print(
                "    excerpt counts: "
                f"selected={context.excerpt_count}, total={context.total_excerpt_count}, "
                f"user={context.total_user_count}, assistant={context.total_assistant_count}"
            )
            if args.compare:
                print("    showing: compare view (selected excerpts vs all excerpts)")
                selected_positions = _selected_excerpt_positions(context.excerpts, context.all_excerpts)
                print("    selected excerpts:")
                for excerpt_index, excerpt in enumerate(context.excerpts, start=1):
                    preview = excerpt.text if args.full else _truncate_preview(excerpt.text)
                    preview = preview.replace("\n", " ")
                    all_index = selected_positions[excerpt_index - 1]
                    print(f"      [{excerpt_index} -> all {all_index}] {excerpt.role}: {preview}")
                print("    all excerpts:")
                for excerpt_index, excerpt in enumerate(context.all_excerpts, start=1):
                    marker = "[selected]" if excerpt_index in selected_positions else "[trimmed ]"
                    preview = excerpt.text if args.full else _truncate_preview(excerpt.text)
                    preview = preview.replace("\n", " ")
                    print(f"      {marker} [{excerpt_index}] {excerpt.role}: {preview}")
            else:
                excerpts = context.all_excerpts if args.all_excerpts else context.excerpts
                label = "all excerpts" if args.all_excerpts else "selected excerpts"
                print(f"    showing: {label}")
                for excerpt_index, excerpt in enumerate(excerpts, start=1):
                    preview = excerpt.text if args.full else _truncate_preview(excerpt.text)
                    preview = preview.replace("\n", " ")
                    print(f"      [{excerpt_index}] {excerpt.role}: {preview}")
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


def _collect_contexts(root: Path, tool: str) -> list:
    contexts = []
    candidates = _collect_context_candidates(root, tool, limit=1)
    for tool_contexts in candidates.values():
        if tool_contexts:
            contexts.append(tool_contexts[0])
    return sorted(contexts, key=lambda context: context.updated_at or "")


def _collect_excerpts(contexts: list) -> list[Excerpt]:
    excerpts: list[Excerpt] = []
    for context in contexts:
        excerpts.extend(context.excerpts)
    return sorted(excerpts, key=lambda excerpt: excerpt.created_at)


def _derive_goal(excerpts: list[Excerpt]) -> str:
    for excerpt in reversed(excerpts):
        if excerpt.role == "user" and excerpt.text:
            return excerpt.text
    return ""


def _build_notes(raw_notes: str, contexts: list) -> str:
    parts = []
    stripped = redact_text(raw_notes).strip()
    if stripped:
        parts.append(stripped)
    if not contexts:
        parts.append("No matching local Codex or Claude transcript was found for this project on the current machine.")
    return "\n\n".join(parts)


def _derive_goal_from_contexts(contexts: list[ExtractedContext], excerpts: list[Excerpt]) -> str:
    scored = sorted(
        [context for context in contexts if context.goal_candidate],
        key=lambda context: (context.score, context.updated_at or ""),
        reverse=True,
    )
    if scored:
        return scored[0].goal_candidate or ""
    return _derive_goal(excerpts)


def _collect_context_candidates(root: Path, tool: str, *, limit: int) -> dict[str, list[ExtractedContext]]:
    candidates: dict[str, list[ExtractedContext]] = {}
    if tool in {"all", "codex"}:
        candidates["codex"] = collect_codex_contexts(root, limit=limit)
    if tool in {"all", "claude"}:
        candidates["claude"] = collect_claude_contexts(root, limit=limit)
    return candidates


def _context_to_dict(context: ExtractedContext) -> dict[str, object]:
    selected_positions = _selected_excerpt_positions(context.excerpts, context.all_excerpts)
    selected_index_by_all_excerpt = {
        all_excerpt_index: selected_index
        for selected_index, all_excerpt_index in enumerate(selected_positions, start=1)
    }
    all_excerpt_index_by_selected = {
        selected_index: all_excerpt_index
        for selected_index, all_excerpt_index in enumerate(selected_positions, start=1)
    }
    return {
        "tool": context.tool,
        "source_kind": context.source_kind,
        "session_id": context.session_id,
        "title": context.title,
        "updated_at": context.updated_at,
        "cwd": context.cwd,
        "transcript_path": context.transcript_path.as_posix() if context.transcript_path else None,
        "score": context.score,
        "score_reasons": context.score_reasons,
        "goal_candidate": context.goal_candidate,
        "excerpt_count": context.excerpt_count,
        "total_excerpt_count": context.total_excerpt_count,
        "total_user_count": context.total_user_count,
        "total_assistant_count": context.total_assistant_count,
        "all_excerpts": [
            {
                "role": excerpt.role,
                "created_at": excerpt.created_at,
                "text": excerpt.text,
                "selected": excerpt_index in selected_index_by_all_excerpt,
                "selected_index": selected_index_by_all_excerpt.get(excerpt_index),
            }
            for excerpt_index, excerpt in enumerate(context.all_excerpts, start=1)
        ],
        "excerpts": [
            {
                "role": excerpt.role,
                "created_at": excerpt.created_at,
                "text": excerpt.text,
                "selected_index": excerpt_index,
                "all_excerpt_index": all_excerpt_index_by_selected.get(excerpt_index),
            }
            for excerpt_index, excerpt in enumerate(context.excerpts, start=1)
        ],
    }


def _manifest_context_entry(context: ExtractedContext) -> dict[str, object]:
    return {
        "tool": context.tool,
        "source_kind": context.source_kind,
        "session_id": context.session_id,
        "title": context.title,
        "updated_at": context.updated_at,
        "transcript_path": context.transcript_path.as_posix() if context.transcript_path else None,
        "excerpt_count": context.excerpt_count,
        "total_excerpt_count": context.total_excerpt_count,
        "total_user_count": context.total_user_count,
        "total_assistant_count": context.total_assistant_count,
        "score": context.score,
        "score_reasons": context.score_reasons,
        "goal_candidate": context.goal_candidate,
    }


def _truncate_preview(text: str, *, limit: int = 240) -> str:
    stripped = text.strip()
    if len(stripped) <= limit:
        return stripped
    return stripped[: limit - 1].rstrip() + "…"


def _excerpt_key(excerpt: Excerpt) -> tuple[str, str, str]:
    return (excerpt.role, excerpt.created_at, excerpt.text)


def _selected_excerpt_positions(selected: list[Excerpt], all_excerpts: list[Excerpt]) -> list[int]:
    positions_by_key: dict[tuple[str, str, str], list[int]] = defaultdict(list)
    for index, excerpt in enumerate(all_excerpts, start=1):
        positions_by_key[_excerpt_key(excerpt)].append(index)

    selected_positions: list[int] = []
    for excerpt in selected:
        positions = positions_by_key[_excerpt_key(excerpt)]
        if positions:
            selected_positions.append(positions.pop(0))
    return selected_positions
