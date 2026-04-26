"""Project and Git inspection helpers."""

from __future__ import annotations

import os
import platform
import re
import subprocess
from pathlib import Path


def run_git(args: list[str], cwd: Path, *, strip: bool = True) -> tuple[int, str, str]:
    process = subprocess.run(
        ["git", *args],
        cwd=str(cwd),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    stdout = process.stdout.strip() if strip else process.stdout
    stderr = process.stderr.strip() if strip else process.stderr
    return process.returncode, stdout, stderr


def find_project_root(start: Path) -> Path:
    code, out, _ = run_git(["rev-parse", "--show-toplevel"], start)
    if code == 0 and out:
        return Path(out).resolve()
    return start.resolve()


def is_git_repo(root: Path) -> bool:
    code, _, _ = run_git(["rev-parse", "--is-inside-work-tree"], root)
    return code == 0


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9._-]+", "-", value)
    value = value.strip("-._")
    return value or "project"


def default_project_id(root: Path) -> str:
    if is_git_repo(root):
        code, out, _ = run_git(["remote", "get-url", "origin"], root)
        if code == 0 and out:
            name = out.rstrip("/").split("/")[-1]
            if name.endswith(".git"):
                name = name[:-4]
            return slugify(name)
    return slugify(root.name)


def git_info(root: Path) -> dict[str, object]:
    info: dict[str, object] = {
        "is_git_repo": is_git_repo(root),
        "git_remote": None,
        "branch": None,
        "head": None,
        "dirty": None,
        "status_short": "",
    }
    if not info["is_git_repo"]:
        return info

    for key, args in {
        "git_remote": ["remote", "get-url", "origin"],
        "branch": ["branch", "--show-current"],
        "head": ["rev-parse", "--short", "HEAD"],
    }.items():
        code, out, _ = run_git(args, root)
        if code == 0 and out:
            info[key] = out

    code, out, _ = run_git(["status", "--short"], root)
    if code == 0:
        info["status_short"] = out
        info["dirty"] = bool(out)
    return info


def device_id() -> str:
    raw = os.environ.get("AISS_DEVICE_ID") or platform.node() or "device"
    return slugify(raw)
