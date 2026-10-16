"""Deterministic golden contracts shared by pytest and Langfuse experiments."""
from __future__ import annotations

import json


def field(output, path):
    for key in path.split("."):
        output = output[int(key)] if isinstance(output, list) else output[key]
    return output


def evaluate_turn(output: dict, contract: dict) -> list[dict]:
    checks = []

    def check(kind, path, expected, predicate):
        try:
            actual = field(output, path)
            passed = bool(predicate(actual))
        except (KeyError, IndexError, TypeError, ValueError, AttributeError):
            actual, passed = None, False
        checks.append({"kind": kind, "field": path, "expected": expected, "actual": actual, "passed": passed})

    for path, expected in contract["expected"].items():
        check("equals", path, expected, lambda actual: actual == expected)
    for path in contract.get("nonempty", []):
        check("nonempty", path, True, bool)
    for path, fragments in contract.get("contains", {}).items():
        for fragment in fragments:
            check("contains", path, fragment, lambda actual: fragment.casefold() in actual.casefold())
    serialized = json.dumps(output, ensure_ascii=False).casefold()
    for fragment in contract.get("forbidden", []):
        checks.append({"kind": "forbidden", "field": "*", "expected": fragment,
                       "actual": "present" if fragment.casefold() in serialized else "absent",
                       "passed": fragment.casefold() not in serialized})
    return checks


def evaluate_conversation(output: dict | None, expected_output: dict) -> list[dict]:
    turns = (output or {}).get("turns", [])
    expected = expected_output["turns"]
    checks = [{"kind": "equals", "field": "turn_count", "expected": len(expected), "actual": len(turns),
               "passed": bool(expected) and len(turns) == len(expected) and not (output or {}).get("error")}]
    for index, contract in enumerate(expected):
        for check in evaluate_turn(turns[index] if index < len(turns) else {}, contract):
            checks.append({**check, "turn": index + 1})
    return checks
