import pytest


@pytest.mark.asyncio
async def test_sdk_receives_evaluation_objects_with_writable_score_fields():
    from langfuse.experiment import _run_evaluator
    from scripts.run_golden_cloud_eval import evaluate_item

    evaluations = await _run_evaluator(evaluate_item, output={"turns": [{"priority": "HIGH"}]},
        expected_output={"turns": [{"expected": {"priority": "HIGH"}}]})
    assert all(hasattr(e, "name") and hasattr(e, "value") for e in evaluations)


def test_evaluator_reports_every_failed_contract_and_missing_fields():
    from eval.golden import evaluate_turn

    checks = evaluate_turn({"priority": "MEDIUM", "reply": "đã đặt lịch", "citations": []}, {
        "expected": {"priority": "HIGH", "routing": "charging_support"},
        "nonempty": ["citations"], "contains": {"reply": ["chờ xác nhận"]},
        "forbidden": ["đã đặt lịch"],
    })
    assert len(checks) == 5
    assert not any(check["passed"] for check in checks)
    assert checks[0]["actual"] == "MEDIUM"


def test_cloud_evaluator_does_not_pass_partial_or_empty_results():
    from scripts.run_golden_cloud_eval import evaluate_item

    expected = {"turns": [{"expected": {"priority": "HIGH"}}, {"expected": {"priority": "HIGH"}}]}
    scores = evaluate_item(output={"turns": [{"priority": "HIGH"}]}, expected_output=expected)
    assert scores[0].name == "golden_pass" and scores[0].value == 0
    assert scores[1].value < 1
    assert evaluate_item(output=None, expected_output=expected)[0].value == 0


def test_cloud_evaluator_passes_a_complete_conversation():
    from scripts.run_golden_cloud_eval import evaluate_item

    scores = evaluate_item(output={"turns": [{"case_brief": {"vehicle_model": "VF5"}}]},
                           expected_output={"turns": [{"expected": {"case_brief.vehicle_model": "VF5"}}]})
    assert all(score.value == 1 for score in scores)


def test_dataset_payload_keeps_inputs_separate_from_contracts():
    from scripts.run_golden_cloud_eval import dataset_payload

    case = {"id": "GOLD-TEST-001", "category": "triage", "label_status": "draft_policy_review",
            "policy_ref": "policy.md", "rationale": "reason", "retrieval": {"status": "NO_SOURCE"},
            "turns": [{"input": "Xe lỗi", "expected": {"priority": "HIGH"}, "nonempty": ["case_id"]}]}
    payload = dataset_payload(case, "hash")
    assert payload["input"]["turns"] == ["Xe lỗi"]
    assert "expected" not in payload["input"]
    assert payload["expected_output"]["turns"] == [{"expected": {"priority": "HIGH"}, "nonempty": ["case_id"]}]
    assert payload["id"] == dataset_payload(case, "hash")["id"]
    assert payload["id"] != dataset_payload(case, "other-hash")["id"]


@pytest.mark.parametrize("missing_metric", [None, "golden_pass", "golden_assertion_accuracy", "golden_pass_rate", "wrong_dataset", "wrong_item"])
def test_cloud_verification_requires_all_trace_links_and_scores(missing_metric):
    import httpx
    from scripts.run_golden_cloud_eval import verify_cloud

    trace_ids = [f"trace-{i}" for i in range(60)]
    metrics = {name: [{"id": f"{name}-{i}", "trace_id": trace, "value": 1, "name": name} for i, trace in enumerate(trace_ids)]
               for name in ("golden_pass", "golden_assertion_accuracy")}
    metrics["golden_pass_rate"] = [{"id": "aggregate", "trace_id": None, "value": 1, "name": "golden_pass_rate"}]
    if missing_metric in metrics:
        metrics[missing_metric].pop()
    def respond(request):
        if request.url.path == "/api/public/experiments":
            data = [{"id": "run", "name": "run", "itemCount": 60, "datasetId": "dataset-id", "scores": metrics["golden_pass_rate"]}]
        else:
            data = [{"traceId": t, "experimentName": "run", "experimentDatasetId": "other" if missing_metric == "wrong_dataset" else "dataset-id",
                     "experimentItemId": "other" if missing_metric == "wrong_item" else f"item-{index}",
                     "scores": [s for name in ("golden_pass", "golden_assertion_accuracy")
                        for s in metrics[name] if s["trace_id"] == t]} for index, t in enumerate(trace_ids)]
        return httpx.Response(200, json={"data": data, "meta": {}})

    client = httpx.Client(base_url="https://cloud.test", transport=httpx.MockTransport(respond))
    result = verify_cloud(client, "dataset", "run", trace_ids, started="2026-10-14T00:00:00+00:00", deadline_s=0,
                          expected_dataset_id="dataset-id", expected_item_ids={f"item-{i}" for i in range(60)})
    assert result["verified"] is (missing_metric is None)
    assert result["scored_traces"] == (59 if missing_metric == "golden_pass" else 60)


def test_cloud_retry_honors_rate_limit_without_reexecuting_model(monkeypatch):
    from scripts.run_golden_cloud_eval import retry_cloud
    from unittest.mock import Mock

    class Limited(Exception):
        status_code = 429
        body = {"details": {"retryAfterSeconds": 30}}

    delays = []
    monkeypatch.setattr("scripts.run_golden_cloud_eval.time.sleep", delays.append)
    call = Mock(side_effect=[Limited(), "saved"])
    assert retry_cloud(call) == "saved"
    assert delays == [31]
    assert call.call_count == 2


def test_local_evidence_preserves_trace_identifiers_while_masking_pii():
    from scripts.run_golden_cloud_eval import safe_records

    rows = [{"trace_id": "abc123456789def", "output": {"reply": "0912345678"}}]
    safe = safe_records(rows)
    assert safe[0]["trace_id"] == rows[0]["trace_id"]
    assert "0912345678" not in safe[0]["output"]["reply"]
