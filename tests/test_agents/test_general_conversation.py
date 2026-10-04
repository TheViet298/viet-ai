from types import SimpleNamespace

import pytest

from src.agents.chatbot_agent import process_chat_message
from src.config import get_settings
from src.services.agent_llm import reset_circuits


@pytest.mark.asyncio
@pytest.mark.parametrize('text', [
    'tôi đang muốn hỏi về pin xe',
    'Pin xe điện hoạt động như thế nào?',
    'Tôi muốn tìm hiểu về xe VF8',
])
async def test_general_question_uses_model_without_creating_case(monkeypatch, text):
    from src.services import llm

    settings = get_settings()
    monkeypatch.setattr(settings, 'agent_llm_enabled', True)
    monkeypatch.setattr(settings, 'google_api_key', 'general-test-key')
    reset_circuits()
    calls = []

    class Model:
        def with_structured_output(self, schema, include_raw):
            self.schema = schema
            return self

        async def ainvoke(self, messages):
            calls.append(messages)
            return {'parsed': self.schema(answer='Anh muốn tìm hiểu cách sạc hay tuổi thọ pin ạ?'),
                    'raw': SimpleNamespace(usage_metadata={})}

    monkeypatch.setattr(llm, 'get_llm', Model)
    result = await process_chat_message(text, user_role='customer', owner='c1')
    assert result['reply'] == 'Anh muốn tìm hiểu cách sạc hay tuổi thọ pin ạ?'
    assert calls
    assert result['case_id'] is None
    assert not result['needs_staff_review']
    assert not result['is_no_source']


@pytest.mark.asyncio
async def test_general_question_model_unavailable_keeps_conversation_open():
    result = await process_chat_message('tôi đang muốn hỏi về pin xe', user_role='customer', owner='c1')
    assert '?' in result['reply']
    assert result['case_id'] is None
    assert not result['needs_staff_review']


@pytest.mark.asyncio
@pytest.mark.parametrize('text', ['Thông số điện áp từng cell pin VF8 là bao nhiêu?',
                                 'Bảo hành pin VF8 bao lâu?'])
async def test_specialist_question_without_evidence_requires_staff(monkeypatch, text):
    from src.services.rag_service import rag_service

    monkeypatch.setattr(rag_service, 'retrieve', lambda *a, **k: {'status': 'NO_SOURCE', 'citations': []})
    result = await process_chat_message(text, user_role='customer', owner='c1')
    assert result['is_no_source']
    assert result['needs_staff_review']
    assert result['case_id']
