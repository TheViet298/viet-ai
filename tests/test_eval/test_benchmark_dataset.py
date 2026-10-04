import os
import json
import pytest

DATASET_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "eval", "datasets"))

REQUIRED_TRIAGE_FIELDS = [
    "id",
    "split",
    "input",
    "expected_intent",
    "expected_priority",
    "expected_missing_fields",
    "expected_response_type",
    "expected_routing",
    "expected_staff_review",
    "expected_safety_trigger",
    "rationale",
]

VALID_INTENTS = [
    "charging_battery",
    "service_incident",
    "sales_general_info",
    "complaint_feedback",
    "safety_adversarial_oos",
]

VALID_PRIORITIES = ["low", "medium", "high", "critical"]

def load_jsonl(filename: str):
    path = os.path.join(DATASET_DIR, filename)
    assert os.path.exists(path), f"File {filename} does not exist in {DATASET_DIR}"
    records = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))
    return records

def test_triage_master_dataset_integrity():
    records = load_jsonl("triage_cases_v1.jsonl")
    assert len(records) >= 40, f"Expected at least 40 cases, got {len(records)}"

    seen_ids = set()
    intents = set()

    for r in records:
        # Check all required fields
        for field in REQUIRED_TRIAGE_FIELDS:
            assert field in r, f"Field '{field}' missing in case {r.get('id')}"

        # Check unique ID
        case_id = r["id"]
        assert case_id not in seen_ids, f"Duplicate ID: {case_id}"
        seen_ids.add(case_id)

        # Check valid intent & priority
        assert r["expected_intent"] in VALID_INTENTS, f"Invalid intent: {r['expected_intent']}"
        assert r["expected_priority"] in VALID_PRIORITIES, f"Invalid priority: {r['expected_priority']}"
        intents.add(r["expected_intent"])

        # Check data types
        assert isinstance(r["expected_missing_fields"], list)
        assert isinstance(r["expected_staff_review"], bool)
        assert isinstance(r["expected_safety_trigger"], bool)
        assert len(r["input"].strip()) > 5

    # All 5 intents must be covered
    assert len(intents) == 5

def test_dataset_splits_distribution():
    train = load_jsonl("triage_train_v1.jsonl")
    dev = load_jsonl("triage_dev_v1.jsonl")
    test = load_jsonl("triage_test_v1.jsonl")

    assert len(train) >= 8, f"Train set too small: {len(train)}"
    assert len(dev) >= 10, f"Dev set too small: {len(dev)}"
    assert len(test) >= 25, f"Test set too small: {len(test)}"

    # Ensure no leakage between train, dev, and test
    train_ids = {r["id"] for r in train}
    dev_ids = {r["id"] for r in dev}
    test_ids = {r["id"] for r in test}

    assert len(train_ids.intersection(test_ids)) == 0, "Data leakage between train and test!"
    assert len(dev_ids.intersection(test_ids)) == 0, "Data leakage between dev and test!"
    assert len(train_ids.intersection(dev_ids)) == 0, "Data leakage between train and dev!"

def test_rag_faq_testset_integrity():
    rag_cases = load_jsonl("rag_test_v1.jsonl")
    assert len(rag_cases) >= 10

    for r in rag_cases:
        assert "id" in r
        assert "query" in r
        assert "expected_response_type" in r
        assert r["expected_response_type"] in ["faq_answer", "no_source"]
        if r["expected_response_type"] == "faq_answer":
            assert r["expected_source_id"] is not None
            assert r["expected_source_id"].startswith("SRC-")
        else:
            assert r["expected_source_id"] is None
