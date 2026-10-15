import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from src.db import Base, get_db
from src.main import app
from src.models.db_models import User
from src.services.auth import get_optional_user, require_customer


@pytest.fixture
def customer_db(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'backend.db'}")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        user = User(id="regression-customer", username="regression", password_hash="unused", role="CUSTOMER")
        db.add(user)
        db.commit()
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[require_customer] = lambda: user
        app.dependency_overrides[get_optional_user] = lambda: user
        yield db
    app.dependency_overrides.clear()
    engine.dispose()


@pytest.mark.asyncio
@pytest.mark.parametrize("message", [
    "Chào bạn, bạn có thể hỗ trợ tôi những gì?",
    "Chào bạn có thể hỗ trợ tôi những gì?",
    "Bạn có thể hỗ trợ tôi những gì?",
    "Bạn làm được gì?",
    "Bạn có thể làm những gì?",
    "Bạn có thể giúp gì cho tôi?",
    "Chào bạn, bạn có thể hỗ trợ những gì cho tôi?",
    "Xin chào! Bạn có những chức năng nào?",
    "chao ban, ban co the ho tro toi nhung gi?",
])
async def test_capabilities_answer_question_without_llm(client, customer_db, monkeypatch, message):
    import src.api.customer as api

    async def unexpected_llm(*args, **kwargs):
        pytest.fail("Capabilities should not require LLM generation")

    monkeypatch.setattr(api, "process_chat_message", unexpected_llm)
    response = await client.post("/api/v1/customer/chat", json={"session_id": "capabilities", "message": message})
    assert response.status_code == 200
    data = response.json()["data"]
    for topic in ["VinFast", "bảo hành", "bảo dưỡng", "sạc", "ứng dụng", "sự cố", "khiếu nại", "hồ sơ"]:
        assert topic in data["message"]
    assert data["case_id"] is None
    assert data["response_type"] == "FAQ_ANSWER"


@pytest.mark.asyncio
@pytest.mark.parametrize("message", ["Chào bạn!", "Xin chào.", "Hello!"])
async def test_pure_greeting_still_greets(client, customer_db, message):
    response = await client.post("/api/v1/customer/chat", json={"session_id": "pure-greeting", "message": message})
    assert response.status_code == 200
    data = response.json()["data"]
    assert "chào" in data["message"].lower()
    assert data["case_id"] is None


@pytest.mark.asyncio
async def test_greeting_with_question_reaches_question_handler(client, customer_db, monkeypatch):
    import src.api.customer as api
    calls = []

    async def faq(text, **kwargs):
        calls.append(text)
        return {"reply": "Thông tin bảo hành từ luồng FAQ", "citations": [], "is_no_source": False}

    monkeypatch.setattr(api, "process_chat_message", faq)
    message = "Chào bạn, thời hạn bảo hành VF8 là bao lâu?"
    response = await client.post("/api/v1/customer/chat", json={"session_id": "greet-question", "message": message})
    assert response.status_code == 200
    assert calls == [message]
    assert "Thông tin bảo hành" in response.json()["data"]["message"]


@pytest.mark.asyncio
async def test_emergency_with_greeting_and_capabilities_is_prioritized(client, customer_db):
    response = await client.post("/api/v1/customer/chat", json={
        "session_id": "greet-emergency", "message": "Chào bạn, bạn có thể hỗ trợ gì? Xe tôi đang bốc khói.",
    })
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["priority"] == "CRITICAL"
    assert data["show_emergency_banner"] is True
    assert data["case_id"]


@pytest.mark.asyncio
async def test_faq_does_not_consume_two_incident_clarifications(client, customer_db, monkeypatch):
    import src.api.customer as api
    async def faq(*args, **kwargs):
        return {"reply": "Xin chào", "citations": [], "is_no_source": True}
    monkeypatch.setattr(api, "process_chat_message", faq)
    for message in ["Xin chào", "Hướng dẫn đặt lịch bảo dưỡng"]:
        response = await client.post("/api/v1/customer/chat", json={"session_id": "new-incident", "message": message})
        assert response.status_code == 200
        assert not response.json()["data"]["citations"]
    for turn in [1, 2]:
        response = await client.post("/api/v1/customer/chat", json={"session_id": "new-incident", "message": "Xe không sạc được"})
        data = response.json()["data"]
        assert data["response_type"] == "CLARIFICATION"
        assert data["clarification_turn"] == turn
        assert data["case_id"] is None
    response = await client.post("/api/v1/customer/chat", json={"session_id": "new-incident", "message": "Xe không sạc được"})
    assert response.json()["data"]["status"] == "Needs Information"
    response = await client.post("/api/v1/customer/chat", json={"session_id": "new-incident", "message": "Xe không sạc được"})
    assert response.json()["data"]["clarification_turn"] == 1


@pytest.mark.asyncio
async def test_faq_preserves_context_and_deduplicates_verified_sources(client, customer_db, monkeypatch):
    import src.api.customer as api
    from src.services.rag_service import source_registry
    source = {**source_registry()["SRC-002"], "source_id": "SRC-002", "applicable_models": ["VF8"], "relevant_snippet": "Thời hạn bảo hành."}
    async def faq(text, **kwargs):
        assert kwargs["session_id"] == "warranty-session"
        assert kwargs["owner"] == "regression-customer"
        assert kwargs["user_role"] == "customer"
        assert kwargs["client_context"]["vehicle_model"] == "VF8"
        return {"reply": "Thông tin đã xác thực.", "citations": [source, source]}
    monkeypatch.setattr(api, "process_chat_message", faq)
    response = await client.post("/api/v1/customer/chat", json={"session_id": "warranty-session", "message": "VF8 được bảo hành bao lâu?", "client_context": {"vehicle_model": "VF8"}})
    assert response.status_code == 200
    citations = response.json()["data"]["citations"]
    assert len(citations) == 1
    assert citations[0]["verified_at"] == source["verified_at"]
    assert citations[0]["relevant_snippet"] == source["relevant_snippet"]


@pytest.mark.asyncio
async def test_battery_topic_uses_conversation_without_case(client, customer_db, monkeypatch):
    from src.agents.nodes import general_node

    async def answer(state, prompt, schema):
        return schema(answer="Anh muốn hỏi về cách sạc hay tuổi thọ pin ạ?")

    monkeypatch.setattr(general_node, "structured_call", answer)
    response = await client.post("/api/v1/customer/chat", json={
        "session_id": "battery-conversation", "message": "tôi đang muốn hỏi về pin xe",
        "client_context": {"vehicle_model": "VF8"},
    })
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["message"] == "Anh muốn hỏi về cách sạc hay tuổi thọ pin ạ?"
    assert data["case_id"] is None

