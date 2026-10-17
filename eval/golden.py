"""Deterministic golden contracts shared by pytest and Langfuse experiments."""
from __future__ import annotations

import json


def equivalent(actual, expected):
    if isinstance(actual, bool) or isinstance(expected, bool):
        return type(actual) is type(expected) and actual == expected
    if isinstance(expected, dict):
        return isinstance(actual, dict) and actual.keys() == expected.keys() and all(
            equivalent(actual[k], v) for k, v in expected.items())
    if isinstance(expected, list):
        return isinstance(actual, list) and len(actual) == len(expected) and all(
            equivalent(a, e) for a, e in zip(actual, expected))
    return actual == expected


def valid_contract(contract):
    allowed = {'input', 'expected', 'nonempty', 'contains', 'contains_any', 'not_contains', 'forbidden'}
    if not isinstance(contract, dict) or set(contract) - allowed:
        return False
    if not isinstance(contract.get('expected', {}), dict):
        return False
    for name in ('nonempty', 'forbidden'):
        if not isinstance(contract.get(name, []), list) or not all(
                isinstance(s, str) and s.strip() for s in contract.get(name, [])):
            return False
    for name in ('contains', 'contains_any', 'not_contains'):
        entries = contract.get(name, {})
        if not isinstance(entries, dict):
            return False
        for path, groups in entries.items():
            if not isinstance(path, str) or not isinstance(groups, list) or not groups:
                return False
            for group in groups:
                options = group if name == 'contains_any' else [group]
                if not isinstance(options, list) or not options or not all(isinstance(s, str) and s for s in options):
                    return False
    return any(contract.get(k) for k in allowed - {'input'})


def field(output, path):
    for key in path.split("."):
        if isinstance(output, list) and not key.isdecimal():
            raise KeyError(key)
        output = output[int(key)] if isinstance(output, list) else output[key]
    return output


def evaluate_turn(output: dict, contract: dict) -> list[dict]:
    if not isinstance(output, dict) or not valid_contract(contract):
        return [{'kind': 'contract', 'field': '*', 'expected': 'valid_nonempty_contract',
                 'actual': 'invalid_contract', 'passed': False}]
    checks = []

    def check(kind, path, expected, predicate):
        try:
            actual = field(output, path)
            passed = bool(predicate(actual))
        except (KeyError, IndexError, TypeError, ValueError, AttributeError):
            actual, passed = None, False
        checks.append({"kind": kind, "field": path, "expected": expected, "actual": actual, "passed": passed})

    for path, expected in contract.get("expected", {}).items():
        check("equals", path, expected, lambda actual: equivalent(actual, expected))
    for path in contract.get("nonempty", []):
        check("nonempty", path, True, bool)
    for path, fragments in contract.get("contains", {}).items():
        for fragment in fragments:
            check("contains", path, fragment, lambda actual: fragment.casefold() in actual.casefold())
    for path, groups in contract.get('contains_any', {}).items():
        for options in groups:
            check('contains_any', path, options, lambda actual: any(s.casefold() in actual.casefold() for s in options))
    for path, fragments in contract.get('not_contains', {}).items():
        for fragment in fragments:
            check('not_contains', path, fragment, lambda actual: fragment.casefold() not in actual.casefold())
    serialized = json.dumps(output, ensure_ascii=False).casefold()
    for fragment in contract.get("forbidden", []):
        checks.append({"kind": "forbidden", "field": "*", "expected": fragment,
                       "actual": "present" if fragment.casefold() in serialized else "absent",
                       "passed": fragment.casefold() not in serialized})
    return checks


def evaluate_conversation(output: dict | None, expected_output: dict) -> list[dict]:
    if not isinstance(output, (dict, type(None))) or not isinstance(expected_output, dict) or not isinstance(
            expected_output.get('turns'), list) or not isinstance((output or {}).get('turns', []), list):
        return [{'kind': 'contract', 'field': '*', 'expected': 'conversation', 'actual': 'invalid_shape', 'passed': False}]
    turns = (output or {}).get("turns", [])
    expected = expected_output["turns"]
    checks = [{"kind": "equals", "field": "turn_count", "expected": len(expected), "actual": len(turns),
               "passed": bool(expected) and len(turns) == len(expected) and not (output or {}).get("error")}]
    for index, contract in enumerate(expected):
        for check in evaluate_turn(turns[index] if index < len(turns) else {}, contract):
            checks.append({**check, "turn": index + 1})
    return checks
