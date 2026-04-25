"""Configuration parsing for AI session sync."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import tomllib

from .schema import DEFAULT_BACKEND, DEFAULT_STORAGE, SYNC_DIR


@dataclass(frozen=True)
class GitBackendConfig:
    remote: str
    branch: str


@dataclass(frozen=True)
class SyncConfig:
    schema_version: str
    project_id: str
    storage: str
    backend_name: str
    git: GitBackendConfig | None = None
    local_path: str | None = None


def load_sync_config(project_root: Path) -> SyncConfig:
    config_path = project_root / SYNC_DIR / "config.toml"
    if not config_path.exists():
        raise SystemExit(f"Sync config not found: {config_path}")

    data = tomllib.loads(config_path.read_text(encoding="utf-8"))
    schema_version = str(data.get("schema_version", ""))
    project_id = str(data.get("project_id", ""))
    storage = str(data.get("storage", DEFAULT_STORAGE))
    backend_table = data.get("backend", {})
    if not isinstance(backend_table, dict):
        backend_table = {}

    git_backend = backend_table.get("git")
    local_backend = backend_table.get("local")
    if storage == "sidecar-repo" or isinstance(git_backend, dict):
        backend_name = "git"
    elif isinstance(local_backend, dict):
        backend_name = "local"
    else:
        backend_name = DEFAULT_BACKEND

    git = None
    if isinstance(git_backend, dict):
        git = GitBackendConfig(
            remote=str(git_backend.get("remote", "")).strip(),
            branch=str(git_backend.get("branch", "main")).strip() or "main",
        )

    local_path = None
    if isinstance(local_backend, dict):
        raw_local_path = str(local_backend.get("path", "")).strip()
        local_path = raw_local_path or None

    return SyncConfig(
        schema_version=schema_version,
        project_id=project_id,
        storage=storage,
        backend_name=backend_name,
        git=git,
        local_path=local_path,
    )


def require_git_sidecar_config(project_root: Path) -> GitBackendConfig:
    config = load_sync_config(project_root)
    if config.storage != "sidecar-repo" or config.backend_name != "git" or config.git is None:
        raise SystemExit("This command requires storage = 'sidecar-repo' with a configured [backend.git] section.")
    if not config.git.remote:
        raise SystemExit("Missing [backend.git].remote in .ai-session-sync/config.toml.")
    return config.git
