"""Measure actual StateGraph outputs against regression and draft eval datasets."""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
import time
from datetime import UTC, datetime
from hashlib import sha256
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


def normalize_answer(text: str) -> str:
    text = text.casefold()
    text = re.sub(r"(?<=\d)[.,](?=\d{3}(?:\D|$))", "", text)
    return re.sub(r"\s+", " ", text).strip()


def grounded_answer(case: dict, out: dict) -> bool:
    ids = {c["source_id"] for c in out.get("rag_citations", [])}
    answer = re.sub(r"(?m)^\[SRC-\d+[^\n]*$", "", out.get("response", ""))
    return (
        out.get("response_type") == "FAQ_ANSWER"
        and case.get("expected_source_id") in ids
        and all(re.search(r"(?<!\w)" + re.escape(normalize_answer(k)) + r"(?!\w)", normalize_answer(answer)) for k in case.get("expected_answer_keywords", []))
        and all(re.search(r"(?<!\w)" + re.escape(normalize_answer(k)) + r"(?!\w)", normalize_answer(answer)) for k in case.get("required_answer_facts", []))
    )


def validate_acceptance_dataset(cases: list[dict]) -> None:
    if len({c["id"] for c in cases}) != len(cases):
        raise ValueError("Duplicate case IDs")
    triage = [c for c in cases if c.get("kind") == "triage"]
    rag = [c for c in cases if c.get("kind") == "rag"]
    if (len(triage) < 60 or len(rag) < 30
        or sum(c.get("expected_priority") == "critical" for c in triage) < 10
        or sum(c.get("expected_response_type") == "no_source" for c in rag) < 10
        or sum(c.get("expected_response_type") == "faq_answer" for c in rag) < 20):
        raise ValueError("Insufficient acceptance coverage")


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
        "mandatory_review_false_negatives": sum(r["needs_review_expected"] and not r.get("needs_review_pred") for r in review),
        "denominators": {
            "critical": len(critical),
            "sourced": len(sourced),
            "no_source": len(no_source),
            "review": len(review),
        },
    }


def generate_markdown_report(metrics: dict, output_path: str | Path, mode: str = "online") -> None:
    lines = [
        "# Báo cáo đánh giá StateGraph",
        "",
        f"Thời điểm UTC: {datetime.now(UTC).isoformat()}",
        f"Chế độ: {mode}. Đo đầu ra thực; thiếu mẫu ghi N/A.",
        "",
        "| Chỉ số | Kết quả | Ngưỡng MVP | Trạng thái |",
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
            f"Mẫu số: `{json.dumps(metrics['denominators'])}`.",
            "Grounding kiểm tra mã nguồn, ranh giới số/từ và dữ kiện bắt buộc trong câu trả lời; chưa chứng minh đúng ngữ nghĩa toàn bộ.",
            "Nhãn có thể mâu thuẫn chính sách HITL; cần duyệt từng ca trước khi nghiệm thu.",
        ]
    )
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


async def run_evaluation_suite(output_dir: str | Path, offline: bool = False, dataset_paths: list[Path] | None = None, mode: str | None = None) -> dict:
    from src.agents.graph import agent
    from src.config import get_settings

    settings = get_settings()
    selected_mode = mode or ("offline" if offline else "online")
    settings.agent_llm_enabled = selected_mode != "offline"
    if selected_mode == "provider_failure":
        from src.services.agent_llm import open_circuit
        open_circuit()
    results = []
    run_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%S")
    paths = dataset_paths or [PROJECT_ROOT / "eval/datasets" / name for name in ("triage_test_v1.jsonl", "rag_test_v1.jsonl")]
    all_cases = [json.loads(line) for path in paths for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if any(c.get("split") == "acceptance" for c in all_cases):
        validate_acceptance_dataset(all_cases)
    labels_approved = all(c.get("label_status") == "approved" for c in all_cases)
    for path in paths:
        cases = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        for case in cases:
            kind = case.get("kind") or ("triage" if "input" in case else "rag")
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
                "response": out.get("response", ""),
                "cited_source_ids": [c["source_id"] for c in out.get("rag_citations", [])],
                "retrieval_diagnostics": out.get("retrieval_diagnostics", {}),
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
                    grounded=grounded_answer(case, out),
                )
            results.append(record)
    metrics = compute_evaluation_metrics(results)
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    from src.services.rag_service import knowledge_fingerprint
    from src.services.session_store import get_store
    with get_store().connect() as db:
        events = [json.loads(row[0]) for row in db.execute("SELECT data FROM agent_traces")]
    llm_events = [e for e in events if e["kind"] == "llm" and e["session_id"].startswith(f"eval-{run_id}-")]
    node_events = [e for e in events if e["kind"] == "node" and e["session_id"].startswith(f"eval-{run_id}-")]
    metadata = {
        "mode": selected_mode,
        "model": settings.model_name,
        "datasets": {str(p.relative_to(PROJECT_ROOT)) if p.is_relative_to(PROJECT_ROOT) else p.name: sha256(p.read_bytes()).hexdigest() for p in paths},
        "prompt_hashes": {p.name: sha256(p.read_bytes()).hexdigest() for p in (PROJECT_ROOT / "prompts").glob("*.md")},
        "llm_outcomes": {decision: sum(e["gate_decision"] == decision for e in llm_events) for decision in sorted({e["gate_decision"] for e in llm_events})},
        "coverage_note": "Configured online includes fallback; parsed events are not complete online cases.",
        "kb_path": settings.chroma_persist_dir,
        "kb_content_sha256": knowledge_fingerprint(settings.chroma_persist_dir) if Path(settings.chroma_persist_dir, "chroma.sqlite3").is_file() else None,
        "kb_sqlite_sha256": sha256(Path(settings.chroma_persist_dir, "chroma.sqlite3").read_bytes()).hexdigest() if Path(settings.chroma_persist_dir, "chroma.sqlite3").is_file() else None,
        "stage_mean_latency_s": {node: sum(e.get("metadata", {}).get("latency_s", 0) for e in node_events if e["node"] == node) / sum(e["node"] == node for e in node_events) for node in {e["node"] for e in node_events}},
        "acceptance_approved": False,
        "label_status": "approved" if labels_approved else "pending_independent_review",
        "kb_version": json.loads(Path(settings.chroma_persist_dir, "build-manifest.json").read_text(encoding="utf-8")) if Path(settings.chroma_persist_dir, "build-manifest.json").is_file() else {"version": "legacy-unversioned"},
        "latency_p50_s": sorted(r["latency_s"] for r in results)[len(results) // 2] if results else None,
        "latency_p95_s": sorted(r["latency_s"] for r in results)[min(len(results) - 1, int(len(results) * 0.95))] if results else None,
    }
    (output / "agent_results.json").write_text(
        json.dumps({"metrics": metrics, "metadata": metadata, "cases": results}, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    generate_markdown_report(
        metrics,
        output / "agent_report.md",
        selected_mode + "; real local Chroma",
    )
    with (output / "agent_report.md").open("a", encoding="utf-8") as report:
        report.write("\nNhãn: " + metadata["label_status"] + ". Kết quả chẩn đoán; chưa phê duyệt nghiệm thu.\n")
    return metrics


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--offline", action="store_true", help="Disable Gemini calls; use real local Chroma retrieval")
    parser.add_argument("--output-dir", default=str(PROJECT_ROOT / "eval/results/agent"))
    parser.add_argument("--mode", choices=["offline", "online", "provider_failure"])
    parser.add_argument("--dataset", action="append", type=Path)
    args = parser.parse_args()
    print(json.dumps(asyncio.run(run_evaluation_suite(args.output_dir, args.offline, args.dataset, args.mode)), indent=2))
