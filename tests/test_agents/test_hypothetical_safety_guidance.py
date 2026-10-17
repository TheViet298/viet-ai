from unittest.mock import AsyncMock

import pytest


@pytest.mark.asyncio
@pytest.mark.parametrize('text', [
    'Xe tôi hiện không bị cháy. Nếu có khói từ pin thì nên làm gì?',
    'Nếu mất phanh thì nên làm gì?',
])
async def test_hypothetical_hazard_uses_controlled_guidance_without_current_incident(monkeypatch, text):
    from src.agents.nodes import general_node as module
    model = AsyncMock(return_value=module.ConversationalAnswer(answer='Dừng ngay lập tức và tắt nguồn.'))
    monkeypatch.setattr(module, 'structured_call', model)
    result = await module.general_node({'latest_user_message': text})
    model.assert_not_awaited()
    assert 'nếu có thể' in result['response']
    assert not result.get('case_brief')
    assert not result.get('suggested_replies')


@pytest.mark.asyncio
async def test_hypothetical_guidance_in_english_does_not_need_translation(monkeypatch):
    from src.services import customer_localization as module
    from src.agents.guardrails import HYPOTHETICAL_SAFE_GUIDANCE
    from src.models.schemas import ChatResponseData
    model = AsyncMock(side_effect=AssertionError('Safety guidance cannot depend on a model'))
    monkeypatch.setattr(module, 'structured_call', model)
    data = ChatResponseData(response_type='FAQ_ANSWER', message=HYPOTHETICAL_SAFE_GUIDANCE)
    await module.localize_response(data, 'en', {})
    assert 'hypothetical' in data.message
    assert not data.show_emergency_banner
    assert data.case_id is None
