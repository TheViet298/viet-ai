import pytest


def test_latency_is_per_case_and_p95_uses_nearest_rank():
    from eval.golden_metrics import build_metrics

    records = [{"id": str(i), "trace_id": str(i), "output": {"duration_s": i, "turns": [{}, {}]}} for i in range(1, 21)]
    rows = [{"id": f"root-{i}", "traceId": str(i), "type": "SPAN"} for i in range(1, 21)]
    metrics = build_metrics(records, rows)
    assert metrics["latency"]["p95_s"] == 19
    assert metrics["latency"]["p50_s"] == 10.5
    assert metrics["total_turns"] == 40
    assert metrics["llm_case_latency"] is None


def test_unknown_usage_is_not_zero_and_duplicate_generations_are_not_counted_twice():
    from eval.golden_metrics import build_metrics

    records = [{"id": "a", "trace_id": "a", "output": {"duration_s": 2, "turns": [{}]}},
               {"id": "b", "trace_id": "b", "output": {"duration_s": 1, "turns": [{}]}}]
    generation = {"id": "g", "traceId": "a", "type": "GENERATION", "usageDetails": {"input": 10, "output": 5, "total": 15}, "totalCost": 0.001}
    metrics = build_metrics(records, [generation, generation])
    assert metrics["cases"][0]["total_tokens"] == 15
    assert metrics["cases"][0]["cost_usd"] == 0.001
    assert metrics["cases"][1]["total_tokens"] is None
    assert metrics["cases"][1]["cost_usd"] is None
    assert metrics["llm_case_latency"]["mean_s"] == 2
    assert not metrics["cloud_coverage_complete"]


def test_observed_case_without_generation_has_zero_model_cost():
    from eval.golden_metrics import build_metrics

    records = [{"id": "a", "trace_id": "a", "output": {"duration_s": 0.1, "turns": [{}]}}]
    metrics = build_metrics(records, [{"id": "root", "traceId": "a", "type": "SPAN"}])
    assert metrics["cases"][0]["total_tokens"] == 0
    assert metrics["cases"][0]["cost_usd"] == 0
    assert metrics["cloud_coverage_complete"]
