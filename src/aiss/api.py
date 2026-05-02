"""Thin desktop data facade over catalog builders."""

from __future__ import annotations

from dataclasses import dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from .catalog import (
    SessionBinding,
    build_project_catalog_from_bindings,
    build_session_catalog_from_bindings,
    build_session_detail_from_binding,
    collect_catalog_sessions,
    find_session_binding,
)
from . import __version__
from .schema import SCHEMA_VERSION

TOOL_FILTERS = {"all", "codex", "claude"}
SORT_FIELDS = {"updated_at", "score", "title"}
SORT_ORDERS = {"asc", "desc"}
ACTIVE_VIEWS = {"session-library", "session-detail", "project-view"}
DATA_MODES = {"fixture", "live"}
STATUS_FILTERS = {"all", "dirty", "patch", "conflict", "warning"}
DEFAULT_API_HOST = "127.0.0.1"
DEFAULT_API_PORT = 8765
FIXTURE_DIRECTORIES = {
    "desktop": Path(__file__).resolve().parents[2] / "docs" / "examples" / "desktop",
    "public-sync-state": Path(__file__).resolve().parents[2] / "docs" / "examples" / "public-sync-state",
}


@dataclass(frozen=True, slots=True)
class SessionQuery:
    tool: str = "all"
    project_id: str | None = None
    status: str | None = None
    q: str = ""
    sort: str = "updated_at"
    order: str = "desc"
    limit: int | None = None


@dataclass(frozen=True, slots=True)
class BundleRequest:
    selected_session_key: str | None = None
    selected_project_id: str | None = None
    active_view: str = "session-library"
    data_mode: str = "live"
    filters: SessionQuery = SessionQuery()


def get_health(project_roots: list[Path] | None = None) -> dict[str, object]:
    roots = _normalize_project_roots(project_roots or [])
    return {
        "schema_version": SCHEMA_VERSION,
        "ok": True,
        "project_roots": [root.as_posix() for root in roots],
        "project_count": len(roots),
        "api": "desktop-facade",
    }


def get_sessions(
    project_roots: list[Path] | None = None,
    *,
    query: SessionQuery | None = None,
) -> dict[str, object]:
    query = query or SessionQuery()
    bindings = query_bindings(project_roots or [], query=query)
    return build_session_catalog_from_bindings(bindings)


def get_session_detail(
    session_key: str,
    project_roots: list[Path] | None = None,
    *,
    include_codex: bool = True,
    include_claude: bool = True,
) -> dict[str, object]:
    bindings = collect_catalog_sessions(
        _normalize_project_roots(project_roots or []),
        include_codex=include_codex,
        include_claude=include_claude,
    )
    binding = find_session_binding(bindings, session_key)
    return build_session_detail_from_binding(binding)


def get_projects(
    project_roots: list[Path] | None = None,
    *,
    query: SessionQuery | None = None,
    selected_project_id: str | None = None,
) -> dict[str, object]:
    query = query or SessionQuery()
    bindings = query_bindings(project_roots or [], query=query)
    resolved_selected = selected_project_id or query.project_id
    return build_project_catalog_from_bindings(bindings, selected_project_id=resolved_selected)


def get_desktop_ui_bundle(
    project_roots: list[Path] | None = None,
    *,
    request: BundleRequest | None = None,
) -> dict[str, object]:
    request = request or BundleRequest()
    _validate_active_view(request.active_view)
    roots = _normalize_project_roots(project_roots or [])
    bindings = query_bindings(roots, query=request.filters)
    session_catalog = build_session_catalog_from_bindings(bindings)
    selected_session_key = request.selected_session_key or _default_selected_session_key(bindings)
    selected_binding = None
    if selected_session_key:
        try:
            selected_binding = find_session_binding(bindings, selected_session_key)
        except KeyError:
            selected_binding = None
    selected_project_id = request.selected_project_id or request.filters.project_id or _default_project_id(bindings)
    project_catalog = build_project_catalog_from_bindings(bindings, selected_project_id=selected_project_id)
    if selected_project_id is None and project_catalog["selected_project"] is not None:
        selected_project_id = project_catalog["selected_project"]["project_id"]
    selected_session_detail = build_session_detail_from_binding(selected_binding) if selected_binding is not None else None
    return {
        "schema_version": SCHEMA_VERSION,
        "bundle_id": _bundle_id(request),
        "generated_at": session_catalog["generated_at"],
        "session_catalog": session_catalog,
        "project_catalog": project_catalog,
        "selected_session_detail": selected_session_detail,
        "view_state": {
            "active_view": request.active_view,
            "selected_session_key": selected_session_key,
            "selected_project_id": selected_project_id,
            "data_mode": request.data_mode,
            "filters": _filters_payload(request.filters),
        },
    }


def rescan_sessions(
    project_roots: list[Path] | None = None,
    *,
    query: SessionQuery | None = None,
) -> dict[str, object]:
    payload = get_sessions(project_roots, query=query)
    return {
        "schema_version": SCHEMA_VERSION,
        "ok": True,
        "session_catalog": payload,
    }


def get_meta(project_roots: list[Path] | None = None) -> dict[str, object]:
    roots = _normalize_project_roots(project_roots or [])
    return {
        "schema_version": SCHEMA_VERSION,
        "version": __version__,
        "api": "desktop-json-server",
        "project_roots": [root.as_posix() for root in roots],
        "supported_tools": sorted(TOOL_FILTERS - {"all"}),
        "supported_statuses": sorted(STATUS_FILTERS - {"all"}),
        "supported_sort_fields": sorted(SORT_FIELDS),
        "supported_sort_orders": sorted(SORT_ORDERS),
        "supported_active_views": sorted(ACTIVE_VIEWS),
        "fixture_groups": sorted(FIXTURE_DIRECTORIES),
    }


def create_api_server(
    project_roots: list[Path] | None = None,
    *,
    host: str = DEFAULT_API_HOST,
    port: int = DEFAULT_API_PORT,
) -> ThreadingHTTPServer:
    roots = _normalize_project_roots(project_roots or [])
    handler = _build_handler(roots)
    return ThreadingHTTPServer((host, port), handler)


def query_bindings(
    project_roots: list[Path],
    *,
    query: SessionQuery,
    include_codex: bool = True,
    include_claude: bool = True,
) -> list[SessionBinding]:
    _validate_query(query)
    roots = _normalize_project_roots(project_roots)
    collect_codex = include_codex and query.tool in {"all", "codex"}
    collect_claude = include_claude and query.tool in {"all", "claude"}
    bindings = collect_catalog_sessions(
        roots,
        include_codex=collect_codex,
        include_claude=collect_claude,
    )
    filtered = [binding for binding in bindings if _binding_matches_query(binding, query)]
    ordered = sorted(filtered, key=lambda binding: _sort_value(binding, query.sort), reverse=(query.order == "desc"))
    if query.limit is not None:
        return ordered[: query.limit]
    return ordered


def _normalize_project_roots(project_roots: list[Path]) -> list[Path]:
    normalized: list[Path] = []
    seen: set[str] = set()
    for root in project_roots:
        resolved = root.expanduser().resolve(strict=False)
        key = resolved.as_posix()
        if key in seen:
            continue
        seen.add(key)
        normalized.append(resolved)
    return normalized


def _validate_query(query: SessionQuery) -> None:
    if query.tool not in TOOL_FILTERS:
        raise ValueError(f"Unsupported tool filter: {query.tool}")
    if query.status is not None and query.status not in STATUS_FILTERS:
        raise ValueError(f"Unsupported status filter: {query.status}")
    if query.sort not in SORT_FIELDS:
        raise ValueError(f"Unsupported sort field: {query.sort}")
    if query.order not in SORT_ORDERS:
        raise ValueError(f"Unsupported sort order: {query.order}")
    if query.limit is not None and query.limit < 1:
        raise ValueError(f"Unsupported limit: {query.limit}")


def _validate_active_view(active_view: str) -> None:
    if active_view not in ACTIVE_VIEWS:
        raise ValueError(f"Unsupported active view: {active_view}")


def _binding_matches_query(binding: SessionBinding, query: SessionQuery) -> bool:
    if query.project_id and binding.project_id != query.project_id:
        return False
    if query.status and query.status != "all" and query.status not in binding.status_flags:
        return False
    needle = query.q.strip().lower()
    if not needle:
        return True
    haystacks = [
        binding.session_key,
        binding.context.title or "",
        binding.context.goal_candidate or "",
        binding.context.session_id or "",
        binding.project_id,
        binding.project_label,
    ]
    return any(needle in haystack.lower() for haystack in haystacks)


def _sort_value(binding: SessionBinding, field: str):
    if field == "score":
        return binding.context.score
    if field == "title":
        return (binding.context.title or "").lower()
    return binding.context.updated_at or ""


def _default_selected_session_key(bindings: list[SessionBinding]) -> str | None:
    if not bindings:
        return None
    return bindings[0].session_key


def _default_project_id(bindings: list[SessionBinding]) -> str | None:
    if not bindings:
        return None
    return bindings[0].project_id


def _filters_payload(query: SessionQuery) -> dict[str, object]:
    return {
        "tool": query.tool,
        "project_id": query.project_id,
        "status": query.status,
        "q": query.q,
        "sort": query.sort,
        "order": query.order,
    }


def _bundle_id(request: BundleRequest) -> str:
    parts = [
        "desktop-ui",
        request.active_view,
        request.filters.tool,
        request.filters.project_id or "all-projects",
    ]
    if request.selected_session_key:
        parts.append(request.selected_session_key.replace(":", "-"))
    return "-".join(parts)


def _build_handler(project_roots: list[Path]):
    class ApiHandler(BaseHTTPRequestHandler):
        server_version = "AISSDesktopAPI/0.1"

        def do_OPTIONS(self) -> None:  # noqa: N802
            self.send_response(HTTPStatus.NO_CONTENT)
            self._write_common_headers("application/json")
            self.end_headers()

        def do_GET(self) -> None:  # noqa: N802
            self._dispatch("GET")

        def do_POST(self) -> None:  # noqa: N802
            self._dispatch("POST")

        def log_message(self, format: str, *args) -> None:  # noqa: A003
            return

        def _dispatch(self, method: str) -> None:
            try:
                parsed = urlparse(self.path)
                path = parsed.path.rstrip("/") or "/"
                params = parse_qs(parsed.query)

                if method == "GET":
                    self._handle_get(path, params)
                    return
                if method == "POST":
                    self._handle_post(path, params)
                    return
                self._respond_json(HTTPStatus.METHOD_NOT_ALLOWED, {"ok": False, "error": "method not allowed"})
            except KeyError as exc:
                self._respond_json(HTTPStatus.NOT_FOUND, {"ok": False, "error": str(exc)})
            except ValueError as exc:
                self._respond_json(HTTPStatus.BAD_REQUEST, {"ok": False, "error": str(exc)})
            except json.JSONDecodeError as exc:
                self._respond_json(HTTPStatus.BAD_REQUEST, {"ok": False, "error": f"invalid json: {exc}"})
            except Exception as exc:  # pragma: no cover - defensive server boundary
                self._respond_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"ok": False, "error": str(exc)})

        def _handle_get(self, path: str, params: dict[str, list[str]]) -> None:
            if path == "/api/health":
                self._respond_json(HTTPStatus.OK, get_health(project_roots))
                return
            if path == "/api/meta":
                self._respond_json(HTTPStatus.OK, get_meta(project_roots))
                return
            if path == "/api/sessions":
                self._respond_json(HTTPStatus.OK, get_sessions(project_roots, query=_query_from_params(params)))
                return
            if path.startswith("/api/sessions/"):
                session_key = unquote(path.removeprefix("/api/sessions/"))
                self._respond_json(HTTPStatus.OK, get_session_detail(session_key, project_roots))
                return
            if path == "/api/projects":
                query = _query_from_params(params)
                self._respond_json(HTTPStatus.OK, get_projects(project_roots, query=query))
                return
            if path.startswith("/api/projects/"):
                project_id = unquote(path.removeprefix("/api/projects/"))
                query = _query_from_params(params, project_id=project_id)
                self._respond_json(
                    HTTPStatus.OK,
                    get_projects(project_roots, query=query, selected_project_id=project_id),
                )
                return
            if path == "/api/ui-bundle":
                request = _bundle_request_from_params(params)
                self._respond_json(HTTPStatus.OK, get_desktop_ui_bundle(project_roots, request=request))
                return
            if path == "/api/dev/fixture-index":
                self._respond_json(HTTPStatus.OK, _fixture_index_payload())
                return
            if path.startswith("/api/dev/fixture/"):
                fixture_name = unquote(path.removeprefix("/api/dev/fixture/"))
                self._respond_json(HTTPStatus.OK, _load_fixture_payload(fixture_name))
                return
            self._respond_json(HTTPStatus.NOT_FOUND, {"ok": False, "error": f"unknown route: {path}"})

        def _handle_post(self, path: str, params: dict[str, list[str]]) -> None:
            if path != "/api/sessions/rescan":
                self._respond_json(HTTPStatus.NOT_FOUND, {"ok": False, "error": f"unknown route: {path}"})
                return
            body = self._read_json_body()
            requested_tools = body.get("tools") if isinstance(body, dict) else None
            rescanned_tools = _requested_tools(requested_tools)
            tool_filter = "all" if set(rescanned_tools) == {"codex", "claude"} else rescanned_tools[0]
            query = _query_from_params(params, tool=tool_filter)
            catalog = get_sessions(project_roots, query=query)
            self._respond_json(
                HTTPStatus.OK,
                {
                    "schema_version": SCHEMA_VERSION,
                    "ok": True,
                    "rescanned_tools": rescanned_tools,
                    "session_count": len(catalog["sessions"]),
                    "project_count": len(catalog["projects"]),
                    "generated_at": catalog["generated_at"],
                },
            )

        def _read_json_body(self) -> dict[str, object]:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0:
                return {}
            raw = self.rfile.read(length).decode("utf-8")
            if not raw.strip():
                return {}
            payload = json.loads(raw)
            if not isinstance(payload, dict):
                raise ValueError("request body must be a JSON object")
            return payload

        def _respond_json(self, status: HTTPStatus, payload: dict[str, object]) -> None:
            encoded = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
            self.send_response(status)
            self._write_common_headers("application/json; charset=utf-8", len(encoded))
            self.end_headers()
            self.wfile.write(encoded)

        def _write_common_headers(self, content_type: str, content_length: int | None = None) -> None:
            self.send_header("Content-Type", content_type)
            if content_length is not None:
                self.send_header("Content-Length", str(content_length))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.send_header("Cache-Control", "no-store")

    return ApiHandler


def _query_from_params(
    params: dict[str, list[str]],
    *,
    tool: str | None = None,
    project_id: str | None = None,
) -> SessionQuery:
    return SessionQuery(
        tool=tool or _param(params, "tool", default="all"),
        project_id=project_id if project_id is not None else _optional_param(params, "project_id"),
        status=_normalize_status(_optional_param(params, "status")),
        q=_param(params, "q", default=""),
        sort=_param(params, "sort", default="updated_at"),
        order=_param(params, "order", default="desc"),
        limit=_optional_int(params, "limit"),
    )


def _bundle_request_from_params(params: dict[str, list[str]]) -> BundleRequest:
    data_mode = _param(params, "data_mode", default="live")
    if data_mode not in DATA_MODES:
        raise ValueError(f"Unsupported data mode: {data_mode}")
    return BundleRequest(
        selected_session_key=_optional_param(params, "selected_session_key"),
        selected_project_id=_optional_param(params, "selected_project_id"),
        active_view=_param(params, "active_view", default="session-library"),
        data_mode=data_mode,
        filters=_query_from_params(params),
    )


def _param(params: dict[str, list[str]], name: str, *, default: str) -> str:
    values = params.get(name)
    if not values:
        return default
    return values[-1]


def _optional_param(params: dict[str, list[str]], name: str) -> str | None:
    value = _param(params, name, default="")
    return value or None


def _optional_int(params: dict[str, list[str]], name: str) -> int | None:
    value = _optional_param(params, name)
    if value is None:
        return None
    try:
        return int(value)
    except ValueError as exc:
        raise ValueError(f"Invalid integer for {name}: {value}") from exc


def _normalize_status(status: str | None) -> str | None:
    if status in {None, "", "all"}:
        return None if status in {None, ""} else "all"
    return status


def _requested_tools(requested_tools: object) -> list[str]:
    if requested_tools is None:
        return ["codex", "claude"]
    if not isinstance(requested_tools, list) or not requested_tools:
        raise ValueError("tools must be a non-empty JSON array when provided")
    values = [str(item) for item in requested_tools]
    if any(value not in {"codex", "claude"} for value in values):
        raise ValueError(f"Unsupported tools: {values}")
    deduped: list[str] = []
    for value in values:
        if value not in deduped:
            deduped.append(value)
    return deduped


def _fixture_index_payload() -> dict[str, object]:
    groups: dict[str, list[str]] = {}
    total = 0
    for group, root in FIXTURE_DIRECTORIES.items():
        names = sorted(path.name for path in root.iterdir() if path.is_file()) if root.exists() else []
        groups[group] = names
        total += len(names)
    return {
        "schema_version": SCHEMA_VERSION,
        "fixture_groups": groups,
        "total_fixtures": total,
    }


def _load_fixture_payload(name: str) -> dict[str, object]:
    fixture_path, source_group = _resolve_fixture_path(name)
    if fixture_path.suffix == ".json":
        return {
            "schema_version": SCHEMA_VERSION,
            "name": name,
            "group": source_group,
            "format": "json",
            "payload": json.loads(fixture_path.read_text(encoding="utf-8")),
        }
    return {
        "schema_version": SCHEMA_VERSION,
        "name": name,
        "group": source_group,
        "format": fixture_path.suffix.lstrip(".") or "text",
        "content": fixture_path.read_text(encoding="utf-8"),
    }


def _resolve_fixture_path(name: str) -> tuple[Path, str]:
    if "/" in name or "\\" in name:
        raise ValueError("fixture name must not contain path separators")
    for group, root in FIXTURE_DIRECTORIES.items():
        candidate = root / name
        if candidate.exists() and candidate.is_file():
            return candidate, group
    raise KeyError(f"Unknown fixture: {name}")
