import pytest
from unittest.mock import patch, AsyncMock
from src.agents.nodes.rag_node import rag_node

@pytest.mark.asyncio
async def test_rag_node_marks_generation_unavailable():
    state = {
        "resolved_query": "VF6 bảo hành bao lâu?",
        "turn": 1,
        "session_id": "test_sess",
        "confidence_score": 0.8,
        "guardrails": {},
    }
    sample_citations = [{
        "source_id": "SRC-002",
        "title": "Chính sách bảo hành xe ô tô VinFast",
        "url": "https://vinfastauto.com/vn_vi/chinh-sach-bao-hanh-oto",
        "relevant_snippet": "Bảo hành xe VF 6 là 7 năm hoặc 160.000 km tuỳ điều kiện nào đến trước.",
        "distance": 0.1,
        "status_code": 200,
        "verified_at": "2026-09-30",
        "applicable_models": ["ALL", "VF6"],
    }]
    mock_retrieval = {
        "status": "SUCCESS",
        "citations": sample_citations,
        "best_distance": 0.1,
        "diagnostics": {"category": "none"},
    }
    with patch("src.agents.nodes.rag_node.vinfast_manual_search", new_callable=AsyncMock, return_value=mock_retrieval):
        with patch("src.agents.nodes.rag_node.valid_citation", return_value=True):
            with patch("src.agents.nodes.rag_node.select_supported_evidence", side_effect=lambda q, c: c):
                with patch("src.agents.nodes.rag_node.structured_call", new_callable=AsyncMock, return_value=None):
                    with patch("src.agents.nodes.rag_node.get_settings") as mock_settings:
                        mock_settings.return_value.agent_turn_timeout_s = 10
                        mock_settings.return_value.rag_retrieval_timeout_s = 5
                        mock_settings.return_value.agent_llm_enabled = True
                        # Reach the generation failure with the supported default
                        # budget; a 4KB prompt now correctly stops at preflight.
                        mock_settings.return_value.agent_context_max_bytes = 8000
                        res = await rag_node(state)
                        assert res["is_no_source"] is True
                        diag = res["retrieval_diagnostics"]
                        assert diag.get("stage") == "generation"
                        assert diag.get("category") == "generation_unavailable"
                        assert "tạo câu trả lời" in res["response"].lower() or "thử lại" in res["response"].lower()

@pytest.mark.asyncio
async def test_session_store_preserves_generation_failure_explanation():
    from src.services.session_store import prepare_application_turn
    data = {
        "is_no_source": True,
        "retrieval_diagnostics": {"stage": "generation", "category": "generation_unavailable"},
        "response": "Tôi chưa hoàn tất được việc tạo câu trả lời từ tài liệu đã tìm thấy. Anh/chị vui lòng thử lại; tôi không thể xác nhận nội dung lúc này.",
    }
    prepare_application_turn(data)
    assert "tạo câu trả lời" in data["response"]
    assert "chưa có nguồn đã xác thực" not in data["response"]
