"""Known repetition defects found by the two-turn topic audit."""
import pytest

pytest_plugins = ["tests.test_api.test_customer_chat_regressions"]


class RepeatedAnswerError(AssertionError):
    """Only the known repetition defect may be treated as expected failure."""


@pytest.mark.asyncio
@pytest.mark.parametrize("first,followup", [
    pytest.param(
        "SOH là gì?", "Sao chưa giải thích rõ SOH được tính như thế nào?",
        id="soh-calculation",
    ),
    pytest.param(
        "Tôi muốn đăng ký lái thử VF8 tại Hà Nội, có lịch nào?", "Sao không có lịch lái thử cụ thể?",
        id="test-drive-availability",
    ),
])
async def test_followup_adds_explanation_instead_of_repeating(client, customer_db, monkeypatch, first, followup):
    from src.agents.nodes import rag_node as node

    async def missing(query, vehicle_model=None):
        return {"status": "NO_SOURCE", "citations": [], "diagnostics": {"category": "no_eligible_evidence"}}

    monkeypatch.setattr(node, "vinfast_manual_search", missing)
    replies = []
    for message in (first, followup):
        response = await client.post("/api/v1/customer/chat", json={
            "session_id": "topic-followup", "message": message,
        })
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["response_type"] == "FAQ_ANSWER"
        assert data["case_id"] is None
        replies.append(" ".join(data["message"].split()))
    if replies[1] == replies[0]:
        raise RepeatedAnswerError("Followup must add an explanation rather than repeat the first answer")
