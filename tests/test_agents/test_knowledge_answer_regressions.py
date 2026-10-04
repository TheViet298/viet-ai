import time

import pytest

from src.agents.nodes import rag_node as node
from src.config import get_settings
from src.services.rag_service import select_supported_evidence, source_registry


def citation(text):
    return {**source_registry()["SRC-007"], "source_id": "SRC-007",
            "applicable_models": ["VF8"], "relevant_snippet": text, "distance": .2}


def test_turtle_question_rejects_lane_and_hud_evidence():
    rows = [citation("Hỗ trợ giữ làn: biểu tượng màu vàng xuất hiện khi LKA hoạt động."),
            citation("Điều chỉnh HUD: chọn biểu tượng trên màn hình trung tâm.")]
    assert select_supported_evidence("biểu tượng con rùa vàng là gì thì", rows) == []


def test_turtle_evidence_retains_only_relevant_complete_section():
    text = "Hỗ trợ giữ làn\nBiểu tượng màu vàng.\nChỉ báo giới hạn công suất\nKhi đèn báo bật, phản hồi chân ga giảm.\nChỉ báo cửa hậu\nCửa hậu mở."
    result = select_supported_evidence("con rùa vàng là gì", [citation(text)])
    assert result
    assert "phản hồi chân ga giảm" in result[0]["relevant_snippet"]
    assert "giữ làn" not in result[0]["relevant_snippet"]
    assert "Cửa hậu" not in result[0]["relevant_snippet"]


@pytest.mark.asyncio
async def test_generation_failure_never_dumps_passages(monkeypatch):
    async def found(*args, **kwargs):
        return {"status": "SUCCESS", "citations": [citation("Hướng dẫn sử dụng xe VF8 có nhiều thông tin trong sổ tay.")], "diagnostics": {}}
    async def failed(*args, **kwargs):
        return None
    monkeypatch.setattr(node, "vinfast_manual_search", found)
    monkeypatch.setattr(node, "structured_call", failed)
    monkeypatch.setattr(get_settings(), "agent_llm_enabled", True)
    result = await node.rag_node({"latest_user_message": "Sổ tay VF8", "confidence_score": .9,
                                  "llm_budget": {"deadline": time.monotonic()+10, "attempts": 0}})
    assert "có nhiều thông tin" not in result["response"]
    assert result["needs_staff_review"]
    assert result["retrieval_diagnostics"]["category"] == "generation_unavailable"

