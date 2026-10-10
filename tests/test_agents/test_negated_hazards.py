import pytest
from src.agents.guardrails import evaluate_hard_safety, without_negated_hazards

def test_negated_smoke_and_smell_is_not_critical():
    # Câu kiểm thử thực tế từ kịch bản 04_unknown_incident lượt 2
    text = "Không có khói hay mùi khét, xe vẫn đi được."
    is_crit, rule, prio = evaluate_hard_safety(text)
    assert is_crit is False, f"Expected non-critical but triggered {rule} with priority {prio}"
    assert prio != "CRITICAL"

def test_negated_smoke_and_smell_with_lan_and_hoac():
    for text in [
        "xe không có khói hoặc mùi khét gì",
        "Không thấy mùi khét lẫn bốc khói",
        "khong co khoi hay mui khet, xe van di duoc",
    ]:
        is_crit, rule, prio = evaluate_hard_safety(text)
        assert is_crit is False, f"Failed on '{text}': triggered {rule}"

def test_negated_one_hazard_but_another_is_present_remains_critical():
    text = "Không có khói nhưng phanh không ăn, xe đang trôi."
    is_crit, rule, prio = evaluate_hard_safety(text)
    assert is_crit is True
    assert rule == "BRAKE_FAILURE"
    assert prio == "CRITICAL"
