"""Offline golden contracts against the real graph and persistent chat bridge."""
import copy
import json
from collections import Counter
from pathlib import Path

import pytest

from eval.golden import evaluate_turn

DATASET = Path(__file__).resolve().parents[2] / "eval/datasets/golden_testcases.jsonl"
CASES = [case for line in DATASET.read_text(encoding="utf-8").splitlines() if line.strip()
         if (case := json.loads(line))['id'].startswith('GOLD-')] if DATASET.exists() else []


def assert_contract(output, turn):
    failures = [check for check in evaluate_turn(output, turn) if not check["passed"]]
    assert not failures, failures


def test_golden_dataset_contract():
    assert DATASET.exists(), "Golden dataset must exist"
    assert len(CASES) == 60
    assert len({case["id"] for case in CASES}) == 60
    assert Counter(case["category"] for case in CASES) == {"safety": 15, "triage": 20, "rag": 15, "multiturn": 10}
    for case in CASES:
        assert case["rationale"] and case["policy_ref"]
        assert case["label_status"] == "draft_policy_review"
        assert case["retrieval"]["status"] in {"SUCCESS", "NO_SOURCE", "TIMEOUT", "ERROR"}
        assert len(case["turns"]) >= (2 if case["category"] == "multiturn" else 1)
        for turn in case["turns"]:
            assert turn["input"].strip() and turn["expected"]
    sourced = [c for c in CASES if c["retrieval"]["status"] == "SUCCESS"]
    assert len(sourced) >= 5
    assert all(c["retrieval"]["citations"] for c in sourced)


def test_contract_detects_wrong_outputs():
    with pytest.raises(AssertionError):
        assert_contract({"priority": "LOW"}, {"expected": {"priority": "CRITICAL"}})
    with pytest.raises(AssertionError):
        assert_contract({"reply": "đã điều phối"}, {"expected": {}, "forbidden": ["đã điều phối"]})
    with pytest.raises(AssertionError):
        assert_contract({"citations": []}, {"expected": {}, "nonempty": ["citations"]})
    with pytest.raises(AssertionError):
        assert_contract({"reply": "khác"}, {"expected": {}, "contains": {"reply": ["1900-232389"]}})


@pytest.mark.asyncio
@pytest.mark.parametrize("case", CASES, ids=[case["id"] for case in CASES])
async def test_golden_case(case, monkeypatch):
    from src.agents.chatbot_agent import process_chat_message
    from src.services.rag_service import rag_service

    monkeypatch.setattr(rag_service, "retrieve", lambda *args, **kwargs: copy.deepcopy(case["retrieval"]))
    for index, turn in enumerate(case["turns"], 1):
        output = await process_chat_message(
            turn["input"], session_id=case["id"], user_role="customer", owner="golden-customer",
        )
        try:
            assert_contract(output, turn)
        except (AssertionError, KeyError, IndexError, TypeError) as error:
            pytest.fail(f"{case['id']} turn {index}: {error}\nActual: {json.dumps(output, ensure_ascii=False, default=str)}")
