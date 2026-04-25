from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def run_cli(tmp_path: Path, *args: str, extra_env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1] / "src")
    if extra_env:
        env.update(extra_env)
    return subprocess.run(
        [sys.executable, "-m", "aiss", *args],
        cwd=tmp_path,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        env=env,
    )


def transcript_timestamp(*, start_minute: int, offset: int) -> str:
    hour = 5 + ((start_minute + offset) // 60)
    minute = (start_minute + offset) % 60
    return f"2026-04-25T{hour:02d}:{minute:02d}:00Z"
