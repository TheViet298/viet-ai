import json

from scripts.run_agent_eval import grounded_answer


def test_unanswered_faq_is_not_grounded():
    case = {"expected_source_id": "SRC-002", "expected_answer_keywords": ["160.000 km"]}
    out = {"response_type": "CLARIFICATION", "response": "160.000 km", "rag_citations": [{"source_id": "SRC-002"}]}
    assert not grounded_answer(case, out)


def test_number_normalization_preserves_value():
    case = {"expected_source_id": "SRC-002", "expected_answer_keywords": ["160.000 km"]}
    out = {"response_type": "FAQ_ANSWER", "response": "Bảo hành 160000 km", "rag_citations": [{"source_id": "SRC-002"}]}
    assert grounded_answer(case, out)
    out["response"] = "Bảo hành 150000 km"
    assert not grounded_answer(case, out)


def test_audit_reports_mismatch_without_rewriting_labels(tmp_path):
    from scripts.audit_agent_eval import audit_results

    dataset = tmp_path / "dataset.jsonl"
    original = json.dumps({"id": "A", "input": "Xe không chạy", "expected_intent": "service_incident"})
    dataset.write_text(original, encoding="utf-8")
    results = tmp_path / "results.json"
    results.write_text(json.dumps({"cases": [{"id": "A", "kind": "triage", "intent_true": "service_incident", "intent_pred": "sales_general_info"}]}), encoding="utf-8")
    audit = audit_results(results, [dataset])
    assert audit[0]["errors"] == ["intent"]
    assert audit[0]["label_status"] == "pending_review"
    assert dataset.read_text(encoding="utf-8") == original
