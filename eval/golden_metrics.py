"""Token/cost readback and case processing latency for golden evaluations."""
from __future__ import annotations

import csv
import json
import math
import statistics

from scripts.langfuse_cloud_evidence import summarize_trace


def latency_summary(values):
    values = sorted(values)
    if not values:
        return None
    return {"cases": len(values), "mean_s": round(statistics.mean(values), 6),
            "p50_s": round(statistics.median(values), 6),
            "p95_s": values[math.ceil(len(values) * 0.95) - 1], "max_s": values[-1]}


def build_metrics(records, observations):
    rows = list({row["id"]: row for row in observations}.values())
    by_trace = {}
    for row in rows:
        by_trace.setdefault(row.get("traceId"), []).append(row)
    cases = []
    for record in records:
        observed = by_trace.get(record["trace_id"], [])
        usage = summarize_trace(observed)
        known_usage = bool(observed) and usage["missing_usage_count"] == 0
        known_cost = bool(observed) and usage["missing_cost_count"] == 0
        cases.append({"id": record["id"], "trace_id": record["trace_id"],
                      "turns": len(record["output"].get("turns", [])),
                      "latency_s": record["output"].get("duration_s"),
                      "generation_count": usage["generation_count"],
                      "input_tokens": usage["known_input_tokens"] if known_usage else None,
                      "output_tokens": usage["known_output_tokens"] if known_usage else None,
                      "total_tokens": usage["known_total_tokens"] if known_usage else None,
                      "cost_usd": usage["known_cost_usd"] if known_cost else None,
                      "usage_complete": known_usage and known_cost})
    selected_rows = [row for row in rows if row.get("traceId") in {r["trace_id"] for r in records}]
    usage = {k: v for k, v in summarize_trace(selected_rows).items() if k not in {"trace_ids", "observation_ids"}}
    return {"total_cases": len(cases), "total_turns": sum(c["turns"] for c in cases),
            "latency_scope": "whole_case_all_turns_excluding_cloud_export_and_readback",
            "latency": latency_summary([c["latency_s"] for c in cases if c["latency_s"] is not None]),
            "llm_case_latency": latency_summary([c["latency_s"] for c in cases if c["generation_count"] and c["latency_s"] is not None]),
            "cloud_usage": usage, "cloud_coverage_complete": bool(cases) and all(c["usage_complete"] for c in cases),
            "cases": cases}


def write_metrics(directory, records, observations):
    metrics = build_metrics(records, observations)
    (directory / "metrics.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with (directory / "case-metrics.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["id", "trace_id", "turns", "latency_s", "generation_count",
                                                   "input_tokens", "output_tokens", "total_tokens", "cost_usd", "usage_complete"])
        writer.writeheader()
        writer.writerows(metrics["cases"])
    usage = metrics["cloud_usage"]
    lines = ["# Token, latency và chi phí", "",
             f"{metrics['total_cases']} case; {metrics['total_turns']} lượt. Token/chi phí lấy từ generation trên Langfuse Cloud.", "",
             "| Input token | Output token | Tổng token đã biết | Chi phí đã biết (USD) |",
             "| ---: | ---: | ---: | ---: |",
             f"| {usage['known_input_tokens']} | {usage['known_output_tokens']} | {usage['known_total_tokens']} | {usage['known_cost_usd']:.10f} |", "",
             "| Nhóm | Số ca | Trung bình (s) | P50 (s) | P95 (s) | Max (s) |",
             "| --- | ---: | ---: | ---: | ---: | ---: |"]
    for name, group in [("Toàn bộ", metrics["latency"]), ("Có gọi LLM", metrics["llm_case_latency"])]:
        if group:
            lines.append(f"| {name} | {group['cases']} | {group['mean_s']:.3f} | {group['p50_s']:.3f} | {group['p95_s']:.3f} | {group['max_s']:.3f} |")
    lines += ["", "Latency đo thời gian xử lý toàn bộ các lượt trong một ca, không gồm ghi/đọc Cloud; P95 dùng nearest rank. Không phải latency từng tin nhắn hoặc SLA production.",
              "", f"Coverage Cloud đầy đủ: `{metrics['cloud_coverage_complete']}`. Generation thiếu usage: {usage['missing_usage_count']}; thiếu cost: {usage['missing_cost_count']}.",
              "Giá trị thiếu được ghi null/trống trong JSON/CSV, không thay bằng 0. Ca có trace nhưng không có generation ghi nhận 0 token/chi phí model.",
              "", "Chi phí là số Cloud ghi nhận, chưa đối chiếu hóa đơn provider. Chi tiết từng ca: [case-metrics.csv](case-metrics.csv)."]
    (directory / "metrics.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return metrics
