"""Measure actual StateGraph outputs against triage and RAG holdout datasets."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

INTENT_NAMES = {
    "Charging/Battery": "charging_battery",
    "Service/Incident": "service_incident",
    "Sales/General Info": "sales_general_info",
    "Complaint/Feedback": "complaint_feedback",
    "Out_of_Scope": "safety_adversarial_oos",
}
TARGETS = {
    "critical_safety_recall": 1.0,
    "intent_accuracy": 0.85,
    "routing_accuracy": 0.80,
    "top_k_grounded_citation_rate": 0.85,
    "no_source_compliance": 0.80,
    "avg_latency_s": 2.5,
    "staff_review_compliance": 0.85,
}


def compute_evaluation_metrics(results: list[dict]) -> dict:
    triage = [r for r in results if r.get("kind") == "triage"]
    rag = [r for r in results if r.get("kind") == "rag"]
    critical = [r for r in triage if r.get("is_critical_true")]
    sourced = [r for r in rag if r.get("is_no_source_expected") is False]
    no_source = [r for r in rag if r.get("is_no_source_expected") is True]
    review = [r for r in triage if "needs_review_expected" in r]

    def rate(items, predicate):
        return round(sum(bool(predicate(r)) for r in items) / len(items), 4) if items else None

    return {
        "total_cases": len(results),
        "triage_cases": len(triage),
        "rag_cases": len(rag),
        "critical_safety_recall": rate(critical, lambda r: r.get("is_critical_pred")),
        "intent_accuracy": rate(triage, lambda r: r.get("intent_true") == r.get("intent_pred")),
        "routing_accuracy": rate(triage, lambda r: r.get("routing_true") == r.get("routing_pred")),
        "top_k_grounded_citation_rate": rate(sourced, lambda r: r.get("grounded")),
        "no_source_compliance": rate(no_source, lambda r: r.get("is_no_source_pred")),
        "avg_latency_s": round(sum(r["latency_s"] for r in results) / len(results), 3) if results else None,
        "staff_review_compliance": rate(review, lambda r: r["needs_review_expected"] == r.get("needs_review_pred")),
        "denominators": {
            "critical": len(critical),
            "sourced": len(sourced),
            "no_source": len(no_source),
            "review": len(review),
        },
    }


def generate_markdown_report(metrics: dict, output_path: str | Path, mode: str = "online") -> None:
    lines = [
        "# StateGraph evaluation",
        "",
        f"Time: {datetime.now(UTC).isoformat()}",
        f"Mode: {mode}. Measured outputs; no substitute predictions. Missing samples report N/A.",
        "",
        "| Metric | Result | MVP target | Status |",
        "|---|---:|---:|---|",
    ]
    for key, target in TARGETS.items():
        value = metrics[key]
        passed = value is not None and (value <= target if key == "avg_latency_s" else value >= target)
        lines.append(
            f"| {key} | {value if value is not None else 'N/A'} | {target} | {'PASS' if passed else 'N/A' if value is None else 'FAIL'} |"
        )
    lines.extend(
        [
            "",
            f"Sample counts: `{json.dumps(metrics['denominators'])}`.",
            "Citation grounding checks expected source and answer keywords; it is not a semantic truth proof.",
            "Dataset labels may conflict with current mandatory HITL policy; inspect per-case results before changing rules.",
        ]
    )
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


async def run_evaluation_suite(output_dir: str | Path, offline: bool = False) -> dict:
    from src.agents.graph import agent
    from src.config import get_settings

    settings = get_settings()
    if offline:
        settings.agent_llm_enabled = False
    results = []
    run_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%S")
    for kind, filename in (("triage", "triage_test_v1.jsonl"), ("rag", "rag_test_v1.jsonl")):
        path = PROJECT_ROOT / "eval/datasets" / filename
        cases = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        for case in cases:
            text = case["input"] if kind == "triage" else case["query"]
            start = time.perf_counter()
            out = await agent.ainvoke(
                {"query": text, "session_id": f"eval-{run_id}-{case['id']}", "user_role": "customer"}
            )
            elapsed = time.perf_counter() - start
            record = {
                "id": case["id"],
                "kind": kind,
                "latency_s": elapsed,
                "is_critical_pred": bool(out.get("is_critical")),
                "routing_pred": out.get("routing"),
                "needs_review_pred": bool(out.get("needs_staff_review")),
                "is_no_source_pred": bool(out.get("is_no_source")),
                "response_type": out.get("response_type"),
            }
            if kind == "triage":
                predicted_intent = (
                    "safety_adversarial_oos"
                    if out.get("is_critical") or out.get("policy_blocked")
                    else INTENT_NAMES.get(out.get("intent"))
                )
                record.update(
                    intent_true=case["expected_intent"],
                    intent_pred=predicted_intent,
                    routing_true=case["expected_routing"],
                    is_critical_true=case["expected_priority"] == "critical",
                    needs_review_expected=case["expected_staff_review"],
                )
            else:
                ids = {citation["source_id"] for citation in out.get("rag_citations", [])}
                refusal_without_source = out.get("response_type") in {"OUT_OF_SCOPE", "SAFETY_REFUSAL"} and not ids
                record.update(
                    is_no_source_expected=case["expected_response_type"] == "no_source",
                    is_no_source_pred=bool(out.get("is_no_source")) or refusal_without_source,
                    fallback_kind="boundary_refusal"
                    if refusal_without_source
                    else "no_source"
                    if out.get("is_no_source")
                    else "answer",
                    grounded=case.get("expected_source_id") in ids
                    and all(
                        keyword.casefold() in out.get("response", "").casefold()
                        for keyword in case.get("expected_answer_keywords", [])
                    ),
                )
            results.append(record)
    metrics = compute_evaluation_metrics(results)
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    (output / "agent_results.json").write_text(
        json.dumps({"metrics": metrics, "cases": results}, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    generate_markdown_report(
        metrics,
        output / "agent_report.md",
        "offline LLM; real local Chroma" if offline else "configured LLM and local Chroma",
    )
    return metrics


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--offline", action="store_true", help="Disable Gemini calls; use real local Chroma retrieval")
    parser.add_argument("--output-dir", default=str(PROJECT_ROOT / "eval/results/agent"))
    args = parser.parse_args()
    print(json.dumps(asyncio.run(run_evaluation_suite(args.output_dir, args.offline)), indent=2))
