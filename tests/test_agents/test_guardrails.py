import pytest

from src.agents.guardrails import (
    check_clarification_boundary,
    check_missing_fields,
    evaluate_hard_safety,
    is_hitl_mandatory,
    sanitize_pii,
)
from src.agents.state import AgentState


class TestPIISanitizer:
    def test_redact_phone_number(self):
        text = "Số điện thoại của tôi là 0912345678, vui lòng gọi lại."
        sanitized, detected, types = sanitize_pii(text)
        assert detected is True
        assert "phone" in types
        assert "0912345678" not in sanitized
        assert "[REDACTED_PHONE]" in sanitized

    def test_redact_cccd(self):
        text = "Số CCCD của tôi là 001234567890."
        sanitized, detected, types = sanitize_pii(text)
        assert detected is True
        assert "national_id" in types
        assert "001234567890" not in sanitized
        assert "[REDACTED_NATIONAL_ID]" in sanitized

    def test_redact_license_plate(self):
        text = "Xe tôi biển số 29A-98765 đang đỗ ở trạm sạc."
        sanitized, detected, types = sanitize_pii(text)
        assert detected is True
        assert "license_plate" in types
        assert "29A-98765" not in sanitized
        assert "[REDACTED_LICENSE_PLATE]" in sanitized

    def test_clean_text_no_pii(self):
        text = "Xe VF8 của tôi không sạc được tại trạm Metropolis."
        sanitized, detected, types = sanitize_pii(text)
        assert detected is False
        assert types == []
        assert sanitized == text


class TestHardSafetyRules:
    @pytest.mark.parametrize("text", ["Xe vẫn chạy bình thường", "Xe đang chạy trên cao tốc", "Xe dang chay binh thuong"])
    def test_running_vehicle_is_not_fire(self, text):
        assert evaluate_hard_safety(text)[0] is False

    @pytest.mark.parametrize("text", ["Xe cháy khi đang chạy", "Xe bi chay", "Xe dang chay va boc khoi", "Xe có khói"])
    def test_fire_still_overrides_running_context(self, text):
        assert evaluate_hard_safety(text) == (True, "SMOKE_OR_FIRE", "CRITICAL")

    def test_smoke_fire_critical(self):
        # TEST-005 in triage_cases_v1.jsonl
        text = "Xe VF e34 của tôi đang bị bốc khói nhẹ ở đầu xe và có mùi khét."
        is_crit, rule, priority = evaluate_hard_safety(text)
        assert is_crit is True
        assert rule == "SMOKE_OR_FIRE"
        assert priority == "CRITICAL"

    def test_brake_failure_critical(self):
        # TEST-011 in triage_cases_v1.jsonl
        text = "Tôi đang đi xe VF7 thì chân phanh bị hẫng, đạp sát sàn xe không giảm tốc độ."
        is_crit, rule, priority = evaluate_hard_safety(text)
        assert is_crit is True
        assert rule == "BRAKE_FAILURE"
        assert priority == "CRITICAL"

    def test_accelerator_jam_critical(self):
        text = "Xe tôi bị kẹt chân ga khi đang di chuyển!"
        is_crit, rule, priority = evaluate_hard_safety(text)
        assert is_crit is True
        assert rule == "ACCELERATOR_JAM"
        assert priority == "CRITICAL"

    def test_turtle_on_highway_critical(self):
        # TEST-003 in triage_cases_v1.jsonl
        text = "Xe VF9 của tôi đang chạy trên cao tốc Pháp Vân thì hiện biểu tượng rùa vàng, đạp ga không lên và xe bị giật."
        is_crit, rule, priority = evaluate_hard_safety(text)
        assert is_crit is True
        assert rule == "TURTLE_ON_HIGHWAY"
        assert priority == "CRITICAL"

    def test_turtle_normal_condition_high_not_critical(self):
        # TEST-004 in triage_cases_v1.jsonl
        text = "Taplo xe VF5 hiện biểu tượng con rùa màu vàng khi khởi động ở bãi đỗ xe nhà, xe vẫn đi lại bình thường trong ngõ."
        is_crit, rule, priority = evaluate_hard_safety(text)
        assert is_crit is False
        assert rule == "TURTLE_NORMAL"
        assert priority == "HIGH"

    def test_normal_charging_issue(self):
        # TEST-001 in triage_cases_v1.jsonl
        text = "Tôi đang ở trạm sạc Vincom Metropolis, cắm súng DC vào xe VF8 nhưng đèn trụ nháy đỏ."
        is_crit, rule, priority = evaluate_hard_safety(text)
        assert is_crit is False
        assert rule is None
        assert priority == "MEDIUM"


class TestClarificationBoundary:
    def test_boundary_within_limit(self):
        assert check_clarification_boundary(0, max_turns=2) is True
        assert check_clarification_boundary(1, max_turns=2) is True

    def test_boundary_reached(self):
        assert check_clarification_boundary(2, max_turns=2) is False
        assert check_clarification_boundary(3, max_turns=2) is False


class TestMissingFields:
    def test_charging_intent_missing_fields(self):
        captured = {"vehicle_model": "VF8"}
        missing = check_missing_fields("Charging/Battery", captured)
        assert "station_location" in missing
        assert "error_code" in missing
        assert "vehicle_model" not in missing

    def test_charging_intent_all_present(self):
        captured = {
            "vehicle_model": "VF8",
            "station_location": "Metropolis",
            "error_code": "CC01",
        }
        missing = check_missing_fields("Charging/Battery", captured)
        assert missing == []


class TestHITLMandatory:
    def test_critical_or_high_priority_must_be_hitl(self):
        assert (
            is_hitl_mandatory(
                intent="Service/Incident",
                priority="CRITICAL",
                confidence_score=0.99,
                is_critical=True,
            )
            is True
        )

        assert (
            is_hitl_mandatory(
                intent="Charging/Battery",
                priority="HIGH",
                confidence_score=0.90,
                is_critical=False,
            )
            is True
        )

    def test_faq_high_confidence_can_auto_reply(self):
        # TEST-006: FAQ auto reply permitted
        assert (
            is_hitl_mandatory(
                intent="Sales/General Info",
                priority="LOW",
                confidence_score=0.92,
                is_critical=False,
                rag_score=0.88,
            )
            is False
        )

    def test_faq_low_rag_score_must_be_hitl(self):
        assert (
            is_hitl_mandatory(
                intent="Sales/General Info",
                priority="LOW",
                confidence_score=0.92,
                is_critical=False,
                rag_score=0.55,
            )
            is True
        )

    def test_low_confidence_must_be_hitl(self):
        assert (
            is_hitl_mandatory(
                intent="Sales/General Info",
                priority="LOW",
                confidence_score=0.50,
                is_critical=False,
            )
            is True
        )


class TestAgentStateSchema:
    def test_agent_state_instantiation(self):
        state: AgentState = {
            "session_id": "sess_001",
            "latest_user_message": "Xe báo lỗi sạc",
            "clarification_turn": 1,
            "max_clarification_turns": 2,
            "intent": "Charging/Battery",
            "priority": "HIGH",
            "confidence_score": 0.88,
            "is_critical": False,
            "captured_fields": {"vehicle_model": "VF8"},
            "missing_fields": ["error_code"],
            "ticket_status": "Staff Reviewing",
            "response_type": "CLARIFICATION",
            "suggested_replies": ["Mã lỗi CC01", "Đèn đỏ không mã"],
        }
        assert state["clarification_turn"] == 1
        assert state["priority"] == "HIGH"
        assert state["intent"] == "Charging/Battery"
