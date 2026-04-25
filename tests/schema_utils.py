from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any


class SchemaValidationError(AssertionError):
    pass


def load_schema(name: str) -> dict[str, Any]:
    schema_path = Path(__file__).resolve().parents[1] / "docs" / "schemas" / name
    return json.loads(schema_path.read_text(encoding="utf-8"))


def assert_matches_schema(instance: Any, schema: dict[str, Any]) -> None:
    _validate(instance, schema, root_schema=schema, path="$")


def _validate(instance: Any, schema: dict[str, Any], *, root_schema: dict[str, Any], path: str) -> None:
    if "$ref" in schema:
        _validate(instance, _resolve_ref(root_schema, schema["$ref"]), root_schema=root_schema, path=path)
        return

    if "oneOf" in schema:
        matches = 0
        last_error: SchemaValidationError | None = None
        for option in schema["oneOf"]:
            try:
                _validate(instance, option, root_schema=root_schema, path=path)
            except SchemaValidationError as exc:
                last_error = exc
            else:
                matches += 1
        if matches != 1:
            detail = f" at {path}: expected exactly one matching schema, got {matches}"
            if last_error is not None:
                detail += f" ({last_error})"
            raise SchemaValidationError(detail)
        return

    if "type" in schema:
        expected_types = schema["type"] if isinstance(schema["type"], list) else [schema["type"]]
        if not any(_is_type(instance, expected_type) for expected_type in expected_types):
            raise SchemaValidationError(f"at {path}: expected type {expected_types}, got {type(instance).__name__}")

    if "enum" in schema and instance not in schema["enum"]:
        raise SchemaValidationError(f"at {path}: expected one of {schema['enum']}, got {instance!r}")

    if "const" in schema and instance != schema["const"]:
        raise SchemaValidationError(f"at {path}: expected const {schema['const']!r}, got {instance!r}")

    if isinstance(instance, str):
        if "pattern" in schema and re.search(schema["pattern"], instance) is None:
            raise SchemaValidationError(f"at {path}: {instance!r} does not match pattern {schema['pattern']!r}")
        if schema.get("format") == "date-time":
            _validate_datetime(instance, path)

    if isinstance(instance, int) and not isinstance(instance, bool) and "minimum" in schema:
        if instance < schema["minimum"]:
            raise SchemaValidationError(f"at {path}: expected minimum {schema['minimum']}, got {instance}")

    if isinstance(instance, list):
        if "minItems" in schema and len(instance) < schema["minItems"]:
            raise SchemaValidationError(f"at {path}: expected at least {schema['minItems']} items, got {len(instance)}")
        if "items" in schema:
            for index, item in enumerate(instance):
                _validate(item, schema["items"], root_schema=root_schema, path=f"{path}[{index}]")

    if isinstance(instance, dict):
        properties = schema.get("properties", {})
        required = schema.get("required", [])
        for key in required:
            if key not in instance:
                raise SchemaValidationError(f"at {path}: missing required property {key!r}")
        if schema.get("additionalProperties") is False:
            extra_keys = set(instance) - set(properties)
            if extra_keys:
                raise SchemaValidationError(f"at {path}: unexpected properties {sorted(extra_keys)!r}")
        for key, value in instance.items():
            if key in properties:
                _validate(value, properties[key], root_schema=root_schema, path=f"{path}.{key}")


def _resolve_ref(root_schema: dict[str, Any], ref: str) -> dict[str, Any]:
    if not ref.startswith("#/"):
        raise SchemaValidationError(f"unsupported ref {ref!r}")
    node: Any = root_schema
    for part in ref[2:].split("/"):
        node = node[part]
    if not isinstance(node, dict):
        raise SchemaValidationError(f"ref {ref!r} did not resolve to an object schema")
    return node


def _is_type(instance: Any, expected_type: str) -> bool:
    if expected_type == "object":
        return isinstance(instance, dict)
    if expected_type == "array":
        return isinstance(instance, list)
    if expected_type == "string":
        return isinstance(instance, str)
    if expected_type == "integer":
        return isinstance(instance, int) and not isinstance(instance, bool)
    if expected_type == "boolean":
        return isinstance(instance, bool)
    if expected_type == "null":
        return instance is None
    raise SchemaValidationError(f"unsupported schema type {expected_type!r}")


def _validate_datetime(value: str, path: str) -> None:
    text = value
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        datetime.fromisoformat(text)
    except ValueError as exc:
        raise SchemaValidationError(f"at {path}: invalid date-time {value!r}") from exc
