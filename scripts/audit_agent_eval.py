"""Audit measured mismatches without rewriting benchmark labels."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def audit_results(results_path: Path, dataset_paths: list[Path]) -> list[dict]:
    labels = {}
    for path in dataset_paths:
        labels.update({c["id"]: c for c in (json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip())})
    rows = []
    for case in json.loads(results_path.read_text(encoding="utf-8"))["cases"]:
        errors = []
        for name, expected, actual in (
            ("intent", "intent_true", "intent_pred"),
            ("routing", "routing_true", "routing_pred"),
            ("review", "needs_review_expected", "needs_review_pred"),
        ):
            if expected in case and case[expected] != case.get(actual):
                errors.append(name)
        if case.get("kind") == "rag" and case.get("is_no_source_expected") is False and not case.get("grounded"):
            errors.append("grounding")
        if errors:
            rows.append({"id": case["id"], "errors": errors, "label_status": "pending_review", "original_label": labels.get(case["id"], {}), "observed": case})
    return rows


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("results", type=Path)
    parser.add_argument("--dataset", action="append", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in audit_results(args.results, args.dataset)) + "\n", encoding="utf-8")
