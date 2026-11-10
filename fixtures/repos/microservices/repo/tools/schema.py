"""A small JSON Schema validator: the subset `contracts/` uses, and nothing more.

    errors = validate(instance, schema)          # [] when the instance matches
    schema = contract("events/order.created")    # contracts/events/order.created.json

A keyword this module does not know raises SchemaError instead of passing silently:
a contract must never look checked when it is not.
"""
from __future__ import annotations

import json
import os
import re
from typing import Any

CONTRACTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "contracts")

ANNOTATIONS = {"$id", "title", "description", "deprecated"}
KEYWORDS = {"type", "const", "enum", "minimum", "minLength", "pattern",
            "required", "properties", "additionalProperties", "items", "minItems"}
TYPES = {"string", "integer", "number", "boolean", "object", "array", "null"}


class SchemaError(ValueError):
    """The schema itself is wrong, or uses a keyword this validator does not support."""


def contract(name: str) -> dict[str, Any]:
    """Loads and checks a schema of `contracts/`, named without its extension."""
    with open(os.path.join(CONTRACTS_DIR, name + ".json"), encoding="utf-8") as fh:
        schema = json.load(fh)
    check_schema(schema, name)
    return schema


def check_schema(schema: Any, where: str = "$") -> None:
    """Walks the whole schema, the parts no instance reaches included."""
    if not isinstance(schema, dict):
        raise SchemaError(f"{where}: a schema is an object")
    unknown = sorted(set(schema) - KEYWORDS - ANNOTATIONS)
    if unknown:
        raise SchemaError(f"{where}: unsupported keyword(s) {', '.join(unknown)}")
    for name in _type_names(schema):
        if name not in TYPES:
            raise SchemaError(f"{where}: unknown type {name!r}")
    if not isinstance(schema.get("additionalProperties", True), bool):
        raise SchemaError(f"{where}: additionalProperties must be true or false")
    for key, sub in schema.get("properties", {}).items():
        check_schema(sub, f"{where}.{key}")
    if "items" in schema:
        check_schema(schema["items"], f"{where}[]")


def validate(instance: Any, schema: dict[str, Any]) -> list[str]:
    """Every way `instance` breaks `schema`, one `path: message` line each."""
    check_schema(schema)
    return _validate(instance, schema, "$")


def _type_names(schema: dict[str, Any]) -> list[str]:
    declared = schema.get("type", [])
    return [declared] if isinstance(declared, str) else list(declared)


def _is(instance: Any, name: str) -> bool:
    if name == "null":
        return instance is None
    if name == "boolean":
        return isinstance(instance, bool)
    if name == "integer":  # in Python a bool is an int; in JSON it is not
        return isinstance(instance, int) and not isinstance(instance, bool)
    if name == "number":
        return isinstance(instance, (int, float)) and not isinstance(instance, bool)
    return isinstance(instance, {"string": str, "object": dict, "array": list}[name])


def _name(instance: Any) -> str:
    """The JSON name of a value; the Python name of what JSON does not have, a tuple or a set."""
    return next((name for name in ("null", "boolean", "integer", "number", "string", "object", "array")
                 if _is(instance, name)), type(instance).__name__)


def _validate(instance: Any, schema: dict[str, Any], where: str) -> list[str]:
    names = _type_names(schema)
    if names and not any(_is(instance, name) for name in names):
        return [f"{where}: expected {' or '.join(names)}, got {_name(instance)}"]
    errors: list[str] = []
    if "const" in schema and instance != schema["const"]:
        errors.append(f"{where}: expected {schema['const']!r}")
    if "enum" in schema and instance not in schema["enum"]:
        errors.append(f"{where}: {instance!r} is not one of {schema['enum']}")
    if isinstance(instance, str):
        if len(instance) < schema.get("minLength", 0):
            errors.append(f"{where}: shorter than {schema['minLength']}")
        if "pattern" in schema and not re.search(schema["pattern"], instance):
            errors.append(f"{where}: does not match {schema['pattern']!r}")
    if _is(instance, "number") and "minimum" in schema and instance < schema["minimum"]:
        errors.append(f"{where}: below {schema['minimum']}")
    if isinstance(instance, dict):
        properties = schema.get("properties", {})
        for key in schema.get("required", []):
            if key not in instance:
                errors.append(f"{where}.{key}: required")
        for key, value in instance.items():
            if key in properties:
                errors += _validate(value, properties[key], f"{where}.{key}")
            elif schema.get("additionalProperties", True) is False:
                errors.append(f"{where}.{key}: not declared in the contract")
    if isinstance(instance, list):
        if len(instance) < schema.get("minItems", 0):
            errors.append(f"{where}: fewer than {schema['minItems']} item(s)")
        if "items" in schema:
            for index, item in enumerate(instance):
                errors += _validate(item, schema["items"], f"{where}[{index}]")
    return errors
