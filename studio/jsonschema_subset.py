"""Dependency-free JSON Schema evaluator for the keywords used by Studio schemas.

This is intentionally bounded, not a general Draft 2020-12 implementation. It validates
every keyword currently present in schemas/studio-framework.schema.json and
schemas/signal-to-studio.schema.json, including local $ref and conditional rules.
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import urldefrag


class SchemaValidationError(ValueError):
    pass


def _load(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _pointer(document: object, fragment: str) -> object:
    current = document
    if not fragment:
        return current
    if not fragment.startswith("/"):
        raise SchemaValidationError(f"unsupported JSON pointer: #{fragment}")
    for token in fragment[1:].split("/"):
        token = token.replace("~1", "/").replace("~0", "~")
        if isinstance(current, list):
            current = current[int(token)]
        else:
            current = current[token]
    return current


def _is_type(instance: object, expected: str) -> bool:
    return {
        "object": isinstance(instance, dict),
        "array": isinstance(instance, list),
        "string": isinstance(instance, str),
        "integer": isinstance(instance, int) and not isinstance(instance, bool),
        "number": isinstance(instance, (int, float)) and not isinstance(instance, bool),
        "boolean": isinstance(instance, bool),
        "null": instance is None,
    }[expected]


def validate_instance(instance: object, schema: dict, schema_path: Path, at: str = "$") -> None:
    if "$ref" in schema:
        ref_path, fragment = urldefrag(schema["$ref"])
        target_path = (schema_path.parent / ref_path).resolve() if ref_path else schema_path
        target_schema = _pointer(_load(target_path), fragment)
        validate_instance(instance, target_schema, target_path, at)
        return
    if "const" in schema and instance != schema["const"]:
        raise SchemaValidationError(f"{at}: expected const {schema['const']!r}")
    if "enum" in schema and instance not in schema["enum"]:
        raise SchemaValidationError(f"{at}: value {instance!r} is outside enum")
    if "type" in schema:
        expected = schema["type"] if isinstance(schema["type"], list) else [schema["type"]]
        if not any(_is_type(instance, item) for item in expected):
            raise SchemaValidationError(f"{at}: expected type {expected}, got {type(instance).__name__}")
    if isinstance(instance, dict):
        required = schema.get("required", [])
        missing = [key for key in required if key not in instance]
        if missing:
            raise SchemaValidationError(f"{at}: missing required keys {missing}")
        if len(instance) < schema.get("minProperties", 0):
            raise SchemaValidationError(f"{at}: fewer than minProperties")
        properties = schema.get("properties", {})
        for key, value in instance.items():
            if key in properties:
                validate_instance(value, properties[key], schema_path, f"{at}.{key}")
            elif schema.get("additionalProperties") is False:
                raise SchemaValidationError(f"{at}: unexpected property {key!r}")
        for branch in schema.get("allOf", []):
            if "if" in branch:
                try:
                    validate_instance(instance, branch["if"], schema_path, at)
                except SchemaValidationError:
                    if "else" in branch:
                        validate_instance(instance, branch["else"], schema_path, at)
                else:
                    if "then" in branch:
                        validate_instance(instance, branch["then"], schema_path, at)
            else:
                validate_instance(instance, branch, schema_path, at)
    if isinstance(instance, list):
        if len(instance) < schema.get("minItems", 0):
            raise SchemaValidationError(f"{at}: fewer than minItems")
        if "maxItems" in schema and len(instance) > schema["maxItems"]:
            raise SchemaValidationError(f"{at}: more than maxItems")
        if "items" in schema:
            for index, item in enumerate(instance):
                validate_instance(item, schema["items"], schema_path, f"{at}[{index}]")
    if isinstance(instance, str):
        if len(instance) < schema.get("minLength", 0):
            raise SchemaValidationError(f"{at}: shorter than minLength")
        if "pattern" in schema and not re.search(schema["pattern"], instance):
            raise SchemaValidationError(f"{at}: does not match {schema['pattern']!r}")
        if schema.get("format") == "date-time":
            try:
                datetime.fromisoformat(instance.replace("Z", "+00:00"))
            except ValueError as exc:
                raise SchemaValidationError(f"{at}: invalid date-time") from exc
    if isinstance(instance, (int, float)) and not isinstance(instance, bool):
        if "minimum" in schema and instance < schema["minimum"]:
            raise SchemaValidationError(f"{at}: below minimum")
        if "maximum" in schema and instance > schema["maximum"]:
            raise SchemaValidationError(f"{at}: above maximum")
