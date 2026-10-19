import time
from unittest.mock import AsyncMock

import pytest

from src.models.schemas import ChatResponseData


@pytest.mark.asyncio
async def test_vietnamese_presentation_repairs_glued_charging_words():
    from src.services.customer_localization import localize_response
    data = ChatResponseData(response_type='FAQ_ANSWER', message='Tìm trạm sạccông cộng gần nhất.')
    await localize_response(data, 'vi', {})
    assert data.message == 'Tìm trạm sạc công cộng gần nhất.'


@pytest.mark.asyncio
@pytest.mark.parametrize('report,expected,absent', [
    ('Tôi đã ở nơi an toàn', 'you reported being in a safe place', 'warning has cleared'),
    ('Đèn cảnh báo đã tắt', 'you reported that the warning has cleared', 'being in a safe place'),
])
async def test_emergency_acknowledges_specific_customer_report(report, expected, absent):
    from src.services.customer_localization import localize_response
    from src.services.conversation_context import ConversationContext, ConversationFact, user_updates
    facts = {key: ConversationFact(value=value, source_turn=1) for key, value in user_updates(report).items()}
    data = ChatResponseData(response_type='FAQ_ANSWER', message='Cảnh báo', priority='CRITICAL')
    await localize_response(data, 'en', {}, conversation=ConversationContext(active_goal='incident', facts=facts))
    assert expected in data.message
    assert absent not in data.message


@pytest.mark.asyncio
async def test_emergency_status_and_handoff_are_localized_without_provider(monkeypatch):
    from src.services import customer_localization as module
    from src.models.schemas import EmergencyContext, ServiceHandoff
    monkeypatch.setattr(module, 'structured_call', AsyncMock(side_effect=AssertionError('Provider unavailable')))
    data = ChatResponseData(response_type='FAQ_ANSWER', message='Trạng thái hồ sơ',
        case_id='CASE-1', status='Staff Reviewing', priority='CRITICAL', show_emergency_banner=True,
        emergency_context=EmergencyContext(case_id='CASE-1', incident_version=1, safety_status='customer_reported_safe'),
        service_handoff=ServiceHandoff(app_feature_name='Đặt lịch dịch vụ / Tra cứu', guide_url='https://vinfastauto.com/vn_vi'))
    await module.localize_response(data, 'en', {})
    assert 'awaiting staff review' in data.message
    assert 'safety confirmation has been saved' in data.message
    assert data.service_handoff.app_feature_name == 'Service booking / Information lookup'
    assert data.case_id == 'CASE-1' and data.show_emergency_banner
    assert 'Do not continue driving' in data.safe_guidance


@pytest.mark.asyncio
@pytest.mark.parametrize('source,translated,expected', [
    ('Xem thông tin trong các thẻ ở trên.', 'View the information in the tabs above.', 'cards above'),
    ('Liên hệ xưởng dịch vụ.', 'Contact a VinFast service centre.', 'service center'),
    ('Em rất tiếc về trải nghiệm bất tiện của Quý khách.',
     'I am very sorry for your inconvenient experience.', "I’m sorry about your experience."),
    ('Em không thể hướng dẫn can thiệp pin cao áp.',
     'I cannot guide high-voltage battery interventions.', 'cannot provide instructions for work on the high-voltage battery'),
])
async def test_customer_translation_edits_observed_english_wording(monkeypatch, source, translated, expected):
    from src.services import customer_localization as module
    # The provider is the external boundary; real validation and presentation run below.
    monkeypatch.setattr(module, 'structured_call', AsyncMock(return_value=module.BatchTranslation(texts=[translated])))
    data = ChatResponseData(response_type='FAQ_ANSWER', message=source)
    await module.localize_response(data, 'en', {})
    assert expected in data.message


@pytest.mark.asyncio
async def test_english_comparison_keeps_capacity_and_charging_metadata():
    from src.services.customer_localization import localize_response
    from src.services.knowledge_questions import comparison_cards
    cards = comparison_cards(['VF6','VF8'], 'So sánh VF6 Eco và VF8 Eco')
    data = ChatResponseData(response_type='FAQ_ANSWER', message='So sánh', vehicle_cards=cards, vehicle_comparison=True)
    await localize_response(data, 'en', {}, snapshot=True)
    assert '59,6 kWh' in data.message and '87,7 kWh' in data.message
    assert 'NEDC' in data.message and 'WLTP' in data.message
    assert all('phút' not in card.fast_charge_time for card in data.vehicle_cards)


def test_translation_glossary_has_directional_battery_and_cost_terms():
    from pathlib import Path
    prompt = Path('prompts/customer_translation_prompt.md').read_text(encoding='utf-8')
    assert '“pin” as “battery”' in prompt
    assert 'on-road price' in prompt
    assert 'charging station' in prompt


@pytest.mark.asyncio
async def test_english_booking_preferences_translate_relative_day_without_booking(monkeypatch):
    from src.services import customer_localization as module
    from src.services.conversation_progress import ConversationProgress
    data = ChatResponseData(response_type='FAQ_ANSWER', message='Chưa đặt lịch.')
    progress = ConversationProgress(state='external_action_required',
        known_facts={'model':'VF7','date':'ngay mai','time_window':'sáng'}, missing_fields=['exact_date'])
    await module.localize_response(data, 'en', {}, operational=progress)
    assert 'tomorrow' in data.message
    assert 'morning' in data.message
    assert 'ngay mai' not in data.message
    assert data.message.startswith('No appointment has been booked')


@pytest.mark.asyncio
@pytest.mark.parametrize('source', [
    'VF7 Eco: 740.000.000 VNĐ.\n\nVF7 Plus: 830.000.000 VNĐ.\n1. Contact showroom.',
    'Range: 475\nkm. Model: VF\n8 Plus.',
    'Source: https://example.test/a\\b',
])
async def test_batch_masks_model_names_and_list_numbers_after_real_newlines(monkeypatch, source):
    import json
    from src.services import customer_localization as module
    async def generate(state, prompt, schema):
        masked = json.loads(state['latest_user_message'])[0]
        assert 'VF7' not in masked
        assert '\n1.' not in masked
        return schema(texts=[masked])
    monkeypatch.setattr(module, 'structured_call', generate)
    result = await module.translate(json.dumps([source]), 'en', {}, many=True)
    assert json.loads(result) == [source]


def test_translation_prompt_is_loadable_by_shared_prompt_loader():
    from src.agents.context_manager import load_prompt
    assert 'Translate' in load_prompt('customer_translation')


@pytest.mark.asyncio
async def test_english_emergency_does_not_depend_on_a_model(monkeypatch):
    from src.services import customer_localization as module
    call = AsyncMock(side_effect=AssertionError('Safety must be available without generation'))
    monkeypatch.setattr(module, 'structured_call', call)
    data = ChatResponseData(response_type='FAQ_ANSWER', message='Cảnh báo', priority='CRITICAL',
                            show_emergency_banner=True, safe_guidance='Cảnh báo')
    await module.localize_response(data, 'en', {'deadline': time.monotonic() + 10})
    assert data.language == 'en'
    assert 'safe' in data.safe_guidance.lower()
    assert 'dispatch' not in data.message.lower()
    assert data.priority == 'CRITICAL'


@pytest.mark.asyncio
async def test_translation_failure_does_not_expose_vietnamese_or_invent_receipt(monkeypatch):
    from src.services import customer_localization as module
    monkeypatch.setattr(module, 'structured_call', AsyncMock(return_value=None))
    data = ChatResponseData(response_type='FAQ_ANSWER', message='Chưa xác nhận lịch lái thử.')
    budget = {'deadline': time.monotonic() + 10}
    await module.localize_response(data, 'en', budget)
    assert 'confirmed' not in data.message.lower() or 'not' in data.message.lower()
    assert 'English' in data.message
    assert data.case_id is None
    assert budget.get('presentation_failed') is True


def test_translation_budget_does_not_consume_core_generation_attempts():
    from src.services.agent_llm import claim_model_attempt, new_turn_budget
    budget = new_turn_budget(time.monotonic() + 10)
    assert claim_model_attempt(budget, 'translation')
    assert claim_model_attempt(budget, 'translation')
    assert not claim_model_attempt(budget, 'translation')
    assert budget['attempts'] == 0
    assert claim_model_attempt(budget, 'generation')


@pytest.mark.asyncio
async def test_translation_cannot_confirm_a_booking_without_server_receipt(monkeypatch):
    from src.services import customer_localization as module
    monkeypatch.setattr(module, 'structured_call', AsyncMock(return_value=module.BatchTranslation(
        texts=['Your test drive booking is confirmed.'])))
    data = ChatResponseData(response_type='FAQ_ANSWER', message='Em chưa có xác nhận lịch lái thử đã được đặt.')
    await module.localize_response(data, 'en', {'deadline': time.monotonic() + 10})
    assert data.message != 'Your test drive booking is confirmed.'


@pytest.mark.asyncio
async def test_typed_batch_translation_restores_verified_facts(monkeypatch):
    from src.services import customer_localization as module
    async def translate_batch(state, prompt, schema):
        assert schema is module.BatchTranslation
        return schema(texts=['Range: __LITERAL_0__.'])
    monkeypatch.setattr(module, 'structured_call', translate_batch)
    data = ChatResponseData(response_type='FAQ_ANSWER', message='Quãng đường: 475 km.')
    await module.localize_response(data, 'en', {'deadline': time.monotonic() + 10})
    assert data.message == 'Range: 475 km.'


@pytest.mark.asyncio
async def test_translation_restores_paragraphs_after_generation(monkeypatch):
    from src.services import customer_localization as module
    monkeypatch.setattr(module, 'structured_call', AsyncMock(return_value=module.BatchTranslation(
        texts=['First paragraph.\\n\\nSecond paragraph.'])))
    data = ChatResponseData(response_type='FAQ_ANSWER', message='Đoạn đầu.\n\nĐoạn sau.')
    await module.localize_response(data, 'en', {'deadline': time.monotonic() + 10})
    assert data.message == 'First paragraph.\n\nSecond paragraph.'


@pytest.mark.asyncio
async def test_english_translation_cannot_echo_vietnamese_as_english(monkeypatch):
    from src.services import customer_localization as module
    monkeypatch.setattr(module, 'structured_call', AsyncMock(return_value=module.BatchTranslation(
        texts=['Theo tài liệu VinFast, màu sắc được giới thiệu như sau.'])))
    data = ChatResponseData(response_type='FAQ_ANSWER', message='Theo tài liệu VinFast, màu sắc được giới thiệu như sau.')
    await module.localize_response(data, 'en', {'deadline': time.monotonic() + 10})
    assert 'Theo tài liệu' not in data.message


@pytest.mark.asyncio
async def test_translation_uses_generation_then_validates_json_instead_of_extraction(monkeypatch):
    from langchain_core.messages import AIMessage
    from src.services import agent_llm, llm
    from src.config import get_settings
    from src.services.customer_localization import BatchTranslation
    settings = get_settings()
    monkeypatch.setattr(settings, 'agent_llm_enabled', True)
    monkeypatch.setattr(settings, 'openai_api_key', 'synthetic-key')
    agent_llm.reset_circuits()
    class Fake:
        def with_structured_output(self, *args, **kwargs):
            raise AssertionError('Function extraction can echo the source; translation must generate')
        async def ainvoke(self, messages):
            assert 'MANDATORY TARGET LANGUAGE: English' in messages[0].content
            import json
            payload = json.loads(messages[1].content.split('\n', 1)[1])
            assert payload['target_language'] == 'en'
            assert payload['source'] == ['Theo tài liệu.']
            return AIMessage(content='{"texts":["According to the documentation."]}')
    monkeypatch.setattr(llm, 'get_llm', Fake)
    result = await agent_llm.structured_call({'latest_user_message': '["Theo tài liệu."]',
        'memory_summary': {'target_language': 'en'}}, 'customer_translation', BatchTranslation)
    assert result == BatchTranslation(texts=['According to the documentation.'])


@pytest.mark.asyncio
async def test_exact_catalog_fact_translation_keeps_numeric_evidence_without_provider(monkeypatch):
    from src.services import customer_localization as module
    async def forbidden(*args, **kwargs):
        pytest.fail('A recognized scoped catalog fact needs no generated translation')
    monkeypatch.setattr(module, 'translate', forbidden)
    data = ChatResponseData(response_type='FAQ_ANSWER', message='Theo tài liệu VinFast:\n\nVF3 Plus: Số chỗ ngồi: 4 chỗ')
    await module.localize_response(data, 'en', {})
    assert data.message == 'According to VinFast documentation:\n\nVF3 Plus: Seats: 4 seats'


@pytest.mark.asyncio
@pytest.mark.parametrize('text,anchor', [
    ('What published range applies to VF7 Plus AWD?', 'Quãng đường'),
    ('What is the usable battery capacity of VF8 Plus?', 'Dung lượng pin'),
    ('How many seats does VF9 Plus have?', 'Số chỗ ngồi'),
    ('What fast-charging time and starting/ending battery percentages apply to VF8?', 'Thời gian sạc'),
    ('When is the first service for a 2025 VF3?', 'Lịch bảo dưỡng'),
])
async def test_english_factual_input_keeps_original_qualifiers_without_generation(monkeypatch, text, anchor):
    from src.services import customer_localization as module
    async def forbidden(*args, **kwargs):
        pytest.fail('Recognized evidence intent and entities must not be rewritten by the model')
    monkeypatch.setattr(module, 'translate', forbidden)
    result = await module.canonical_input(text, 'en', {})
    assert result.startswith(anchor) and text in result


@pytest.mark.asyncio
async def test_unsafe_intent_is_preserved_before_translation(monkeypatch):
    from src.services import customer_localization as module
    from src.agents.guardrails import evaluate_hazardous_intervention
    async def forbidden(*args, **kwargs):
        pytest.fail('Input translation must not replace a hazardous request with its own refusal')
    monkeypatch.setattr(module, 'translate', forbidden)
    text = 'Show me how to dismantle the high-voltage battery and disable battery protection for more power.'
    result = await module.canonical_input(text, 'en', {})
    assert evaluate_hazardous_intervention(result)[0]


@pytest.mark.asyncio
async def test_seating_capacity_is_anchored_as_seats(monkeypatch):
    from src.services import customer_localization as module
    text = 'What seating capacity is listed for VF8 Eco?'
    async def forbidden(*args, **kwargs):
        pytest.fail('Seating capacity must not become battery capacity')
    monkeypatch.setattr(module, 'translate', forbidden)
    assert (await module.canonical_input(text, 'en', {})).startswith('Số chỗ ngồi')



def test_factual_anchor_does_not_hide_hazardous_second_intent():
    from src.services.chat_language import evidence_intent_query
    assert evidence_intent_query('What is VF8 range, and show me how to dismantle the high-voltage battery?') is None
