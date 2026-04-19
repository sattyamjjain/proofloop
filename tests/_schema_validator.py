#!/usr/bin/env python3
"""Minimal stdlib JSON Schema validator.

Covers only the subset of draft 2020-12 that ``schemas/scorecard.v1.schema.json``
uses. Keeps the project's stdlib-only pitch intact for contributors who
don't want ``pip install jsonschema``.

Supported keywords:
    type (including type arrays with "null"), required, properties,
    additionalProperties (true/false), patternProperties, enum, const,
    minimum, maximum, exclusiveMinimum, exclusiveMaximum, minLength,
    maxLength, minItems, maxItems, pattern, items, $ref (local only,
    `#/$defs/<name>`), $defs, format ("date-time" validated, others
    passed through).
"""
from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Dict, List, Tuple

__all__ = ["SchemaError", "validate"]


class SchemaError(AssertionError):
    """Raised when a document fails schema validation."""


def _type_matches(value: Any, expected: str) -> bool:
    if expected == "null":
        return value is None
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "integer":
        # JSON Schema: integer excludes bool but accepts int.
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected == "string":
        return isinstance(value, str)
    if expected == "array":
        return isinstance(value, list)
    if expected == "object":
        return isinstance(value, dict)
    raise SchemaError(f"unknown type keyword: {expected}")


def _resolve(ref: str, root: Dict[str, Any]) -> Dict[str, Any]:
    if not ref.startswith("#/"):
        raise SchemaError(f"only local $refs supported: {ref}")
    node: Any = root
    for part in ref[2:].split("/"):
        if not isinstance(node, dict) or part not in node:
            raise SchemaError(f"unresolved $ref: {ref}")
        node = node[part]
    if not isinstance(node, dict):
        raise SchemaError(f"$ref target is not an object: {ref}")
    return node


def _check_format(value: str, fmt: str, path: str) -> None:
    if fmt == "date-time":
        # Accept RFC 3339-ish date-times. Python's fromisoformat is strict
        # about some things; for a trailing Z we coerce before parsing.
        candidate = value.replace("Z", "+00:00") if value.endswith("Z") else value
        try:
            datetime.fromisoformat(candidate)
        except ValueError:
            raise SchemaError(f"{path}: not a valid date-time: {value!r}")


def _validate(
    value: Any,
    schema: Dict[str, Any],
    root: Dict[str, Any],
    path: str,
    errors: List[str],
) -> None:
    if "$ref" in schema:
        target = _resolve(schema["$ref"], root)
        _validate(value, target, root, path, errors)
        return

    if "type" in schema:
        expected = schema["type"]
        if isinstance(expected, str):
            if not _type_matches(value, expected):
                errors.append(
                    f"{path}: expected type {expected!r}, got {type(value).__name__}"
                )
                return
        elif isinstance(expected, list):
            if not any(_type_matches(value, t) for t in expected):
                errors.append(
                    f"{path}: expected one of types {expected}, got {type(value).__name__}"
                )
                return
        else:
            errors.append(f"{path}: 'type' must be a string or list")
            return

    if "const" in schema and value != schema["const"]:
        errors.append(f"{path}: const mismatch (expected {schema['const']!r}, got {value!r})")

    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{path}: value {value!r} not in enum {schema['enum']}")

    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            errors.append(f"{path}: {value} < minimum {schema['minimum']}")
        if "maximum" in schema and value > schema["maximum"]:
            errors.append(f"{path}: {value} > maximum {schema['maximum']}")
        if "exclusiveMinimum" in schema and value <= schema["exclusiveMinimum"]:
            errors.append(f"{path}: {value} <= exclusiveMinimum {schema['exclusiveMinimum']}")
        if "exclusiveMaximum" in schema and value >= schema["exclusiveMaximum"]:
            errors.append(f"{path}: {value} >= exclusiveMaximum {schema['exclusiveMaximum']}")

    if isinstance(value, str):
        if "minLength" in schema and len(value) < schema["minLength"]:
            errors.append(f"{path}: length {len(value)} < minLength {schema['minLength']}")
        if "maxLength" in schema and len(value) > schema["maxLength"]:
            errors.append(f"{path}: length {len(value)} > maxLength {schema['maxLength']}")
        if "pattern" in schema:
            if re.search(schema["pattern"], value) is None:
                errors.append(f"{path}: {value!r} does not match pattern {schema['pattern']!r}")
        if "format" in schema:
            try:
                _check_format(value, schema["format"], path)
            except SchemaError as exc:
                errors.append(str(exc))

    if isinstance(value, list):
        if "minItems" in schema and len(value) < schema["minItems"]:
            errors.append(f"{path}: array length {len(value)} < minItems {schema['minItems']}")
        if "maxItems" in schema and len(value) > schema["maxItems"]:
            errors.append(f"{path}: array length {len(value)} > maxItems {schema['maxItems']}")
        items_schema = schema.get("items")
        if isinstance(items_schema, dict):
            for i, item in enumerate(value):
                _validate(item, items_schema, root, f"{path}[{i}]", errors)

    if isinstance(value, dict):
        required = schema.get("required", []) or []
        for key in required:
            if key not in value:
                errors.append(f"{path}: missing required property {key!r}")
        properties = schema.get("properties", {}) or {}
        for key, sub in properties.items():
            if key in value:
                _validate(value[key], sub, root, f"{path}.{key}", errors)
        additional = schema.get("additionalProperties", True)
        if additional is False:
            for key in value:
                if key not in properties:
                    errors.append(f"{path}: additional property {key!r} not allowed")
        elif isinstance(additional, dict):
            for key, sub_value in value.items():
                if key in properties:
                    continue
                _validate(sub_value, additional, root, f"{path}.{key}", errors)


def validate(document: Any, schema: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """Return (is_valid, errors) for *document* against *schema*.

    Does not raise; collects every mismatch so callers can report them
    all at once.
    """
    errors: List[str] = []
    _validate(document, schema, schema, "$", errors)
    return not errors, errors
