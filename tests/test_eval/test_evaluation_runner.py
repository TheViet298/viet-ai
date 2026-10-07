import pytest


def test_absent_measurements_are_not_reported_as_perfect():
    from scripts.run_agent_eval import compute_evaluation_metrics

    metrics = compute_evaluation_metrics(
        [{"kind": "triage", "intent_true": "service_incident", "intent_pred": "sales_general_info", "latency_s": 0.2}]
    )
    assert metrics["intent_accuracy"] == 0.0
    assert metrics["critical_safety_recall"] is None
    assert metrics["no_source_compliance"] is None


def test_separate_rag_and_triage_metrics():
    from scripts.run_agent_eval import compute_evaluation_metrics

    results = [
        {
            "kind": "triage",
            "is_critical_true": True,
            "is_critical_pred": True,
            "intent_true": "safety_adversarial_oos",
            "intent_pred": "safety_adversarial_oos",
            "routing_true": "emergency_rescue",
            "routing_pred": "emergency_rescue",
            "needs_review_expected": True,
            "needs_review_pred": True,
            "latency_s": 0.1,
        },
        {"kind": "rag", "is_no_source_expected": False, "is_no_source_pred": False, "grounded": True, "latency_s": 0.2},
        {"kind": "rag", "is_no_source_expected": True, "is_no_source_pred": True, "latency_s": 0.3},
    ]
    metrics = compute_evaluation_metrics(results)
    for metric in [
        "critical_safety_recall",
        "intent_accuracy",
        "routing_accuracy",
        "top_k_grounded_citation_rate",
        "no_source_compliance",
        "staff_review_compliance",
    ]:
        assert metrics[metric] == 1.0
    assert metrics["avg_latency_s"] == pytest.approx(0.2)
