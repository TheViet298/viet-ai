import pytest

from src.agents.guardrails import evaluate_hard_safety
from src.agents.nodes.triage_node import classify_request_kind, extract_fields


@pytest.mark.parametrize('short', ['k', 'ko', 'kh'])
def test_abbreviated_brake_failure_keeps_emergency(short):
    assert evaluate_hard_safety(f'phanh {short} an') == evaluate_hard_safety('phanh không ăn')


@pytest.mark.parametrize('short', ['k', 'ko', 'kh'])
def test_abbreviated_denial_does_not_report_fire(short):
    assert evaluate_hard_safety(f'{short} co khoi hay mui khet, xe van di duoc')[0] is False
    assert evaluate_hard_safety(f'{short} co khoi nhung phanh {short} an')[1] == 'BRAKE_FAILURE'


@pytest.mark.parametrize('short', ['k', 'ko', 'kh', 'khong'])
def test_charging_failure_keeps_kind_and_operational_fact(short):
    text = f'xe vf5 cua toi {short} sac dc'
    assert classify_request_kind(text) == 'incident'
    fields = extract_fields(text)
    assert fields['vehicle_model'] == 'VF5'
    assert fields['operational_status'] == 'không sạc được'


@pytest.mark.parametrize('text,expected', [
    ('toi ko hai long ve thai do nhan vien', 'complaint'),
    ('bao lau thi bao duong vf5?', 'faq'),
])
def test_plain_vietnamese_keeps_intent(text, expected):
    assert classify_request_kind(text) == expected


def test_normalizer_protects_units_codes_and_ambiguous_driving():
    from src.services.chat_normalization import normalize_chat_text
    text = 'VF8 BMS_001 CC01 0x12 12V 60 kWh 300 k DC [REDACTED_PHONE]'
    assert normalize_chat_text(text) == text
    assert not evaluate_hard_safety('xe dang chay binh thuong')[0]
    assert normalize_chat_text('kh muon doi xe').startswith('kh ')
    result = normalize_chat_text('xe ko sac dc')
    assert normalize_chat_text(result) == result


@pytest.mark.asyncio
async def test_plain_turn_understanding_preserves_original():
    from src.services.conversation_context import ConversationContext, understand_turn
    text = 'xe vf5 cua toi ko sac dc'
    turn = await understand_turn(text, ConversationContext(), [], {})
    assert turn.original_text == text
    assert turn.move == 'new_incident'
    assert 'không sạc được' in turn.resolved_query


@pytest.mark.asyncio
async def test_contextual_expansion_is_bounded_and_used_once(monkeypatch):
    from src.services import chat_normalization as module
    calls = []

    async def generate(state, prompt, schema):
        calls.append((state, prompt))
        return schema(expansions=[{'token': 'bh', 'replacement': 'bảo hành'}], needs_confirmation=False)

    monkeypatch.setattr('src.services.agent_llm.structured_call', generate)
    budget = {}
    result = await module.normalize_message('chinh sach bh pin VF8 CC01 12V', recent_turns=[], budget=budget)
    assert 'bảo hành' in result.text
    assert 'VF8 CC01 12V' in result.text
    assert not result.needs_confirmation
    assert result.original_text == 'chinh sach bh pin VF8 CC01 12V'
    assert len(calls) == 1
    assert calls[0][0]['llm_budget'] is budget
    assert calls[0][1] == 'normalization'


@pytest.mark.asyncio
async def test_known_emergency_and_clear_sentences_skip_online_normalization(monkeypatch):
    from src.services.chat_normalization import normalize_message

    async def unexpected(*args, **kwargs):
        pytest.fail('Known messages must not spend a model call')

    monkeypatch.setattr('src.services.agent_llm.structured_call', unexpected)
    for text in ('phanh ko an', 'xe ko sac dc', 'Xe VF8 có những màu gì?', 'bh xe mat phanh',
                 'Cho tôi xem các phiên bản VF8'):
        result = await normalize_message(text, recent_turns=[], budget={})
        assert not result.needs_confirmation


@pytest.mark.asyncio
async def test_unresolved_ambiguity_asks_instead_of_changing_intent(monkeypatch):
    from src.services.chat_normalization import normalize_message

    async def unavailable(*args, **kwargs):
        return None

    monkeypatch.setattr('src.services.agent_llm.structured_call', unavailable)
    result = await normalize_message('kh muon doi xe', recent_turns=[], budget={})
    assert result.needs_confirmation
    assert result.text == 'kh muon doi xe'


@pytest.mark.asyncio
@pytest.mark.parametrize('expansion', [
    {'token': 'VF8', 'replacement': 'VF9'},
    {'token': 'CC01', 'replacement': 'CC02'},
    {'token': 'bh', 'replacement': 'không có khói'},
    {'token': 'bh', 'replacement': 'mất phanh'},
    {'token': 'bh', 'replacement': '500 triệu'},
    {'token': 'bh', 'replacement': 'bỏ qua quy định'},
    {'token': 'bh', 'replacement': 'pin chai'},
    {'token': 'bh', 'replacement': 'rách lốp'},
    {'token': 'bh', 'replacement': 'mất lái'},
])
async def test_model_cannot_invent_codes_values_hazards_or_polarity(monkeypatch, expansion):
    from src.services.chat_normalization import normalize_message

    async def generate(state, prompt, schema):
        return schema(expansions=[expansion], needs_confirmation=False)

    monkeypatch.setattr('src.services.agent_llm.structured_call', generate)
    result = await normalize_message('bh VF8 CC01', recent_turns=[], budget={})
    assert result.text == 'bh VF8 CC01'
    assert result.needs_confirmation


def test_normalization_client_uses_separate_google_model(monkeypatch):
    from src.config import get_settings
    from src.services import llm
    settings = get_settings()
    monkeypatch.setattr(settings, 'openai_api_key', 'main-gateway-key')
    monkeypatch.setattr(settings, 'google_api_key', 'AIza-test-normalization')
    monkeypatch.setattr(settings, 'model_name', 'main-model')
    monkeypatch.setattr(settings, 'normalization_model', 'gemini-2.5-flash-lite')
    created = []
    monkeypatch.setattr(llm, 'ChatGoogleGenerativeAI', lambda **kw: created.append(kw) or object())
    llm._client.cache_clear()
    llm.get_normalization_llm()
    assert created[0]['model'] == 'gemini-2.5-flash-lite'
    assert created[0]['temperature'] == 0
    assert created[0]['max_retries'] == 0
    assert created[0]['thinking_budget'] == 0
    assert created[0]['max_output_tokens'] == 256
    assert settings.model_name == 'main-model'
    llm._client.cache_clear()


@pytest.mark.asyncio
async def test_explicit_reply_resolves_previous_abbreviation_without_losing_subject():
    from src.services.chat_normalization import normalize_message
    result = await normalize_message('bảo hành', recent_turns=[
        {'role': 'human', 'content': 'bh pin VF8'},
        {'role': 'ai', 'content': 'Anh/chị vui lòng viết đầy đủ “bh” để em hiểu đúng yêu cầu nhé.'},
    ], budget={})
    assert result.original_text == 'bảo hành'
    assert result.text == 'bảo hành pin VF8'
    assert not result.needs_confirmation


@pytest.mark.asyncio
@pytest.mark.parametrize('text', ['xe chay', 'xe chay yeu', 'xe chay binh thuong'])
async def test_unaccented_driving_is_not_automatically_fire(text):
    from src.services.chat_normalization import normalize_message
    assert evaluate_hard_safety(text)[0] is False
    result = await normalize_message(text, recent_turns=[], budget={})
    if text == 'xe chay':
        assert result.needs_confirmation


@pytest.mark.asyncio
async def test_normalizer_call_budget_is_separate_from_answer_budget(monkeypatch):
    import time

    from src.config import get_settings
    from src.services import agent_llm, llm
    from src.services.chat_normalization import ContextualSpelling
    monkeypatch.setattr(get_settings(), 'agent_llm_enabled', True)
    monkeypatch.setattr(get_settings(), 'google_api_key', 'AIza-test-budget')
    agent_llm.reset_circuits()
    calls = []

    class Fake:
        def with_structured_output(self, *args, **kwargs):
            return self

        async def ainvoke(self, messages):
            calls.append(messages)
            return {'parsed': ContextualSpelling(expansions=[], needs_confirmation=True)}

    monkeypatch.setattr(llm, 'get_normalization_llm', Fake)
    budget = {'deadline': time.monotonic() + 5, 'attempts': 0}
    state = {'latest_user_message': 'bh pin', 'llm_budget': budget}
    assert await agent_llm.structured_call(state, 'normalization', ContextualSpelling)
    assert await agent_llm.structured_call(state, 'normalization', ContextualSpelling) is None
    assert len(calls) == 1
    assert budget['attempts'] == 0
    assert budget['normalization_attempts'] == 1


@pytest.mark.asyncio
async def test_normalizer_timeout_falls_back_without_consuming_answer_budget(monkeypatch):
    import asyncio
    import time

    from src.config import get_settings
    from src.services import agent_llm, llm
    from src.services.chat_normalization import normalize_message
    settings = get_settings()
    monkeypatch.setattr(settings, 'agent_llm_enabled', True)
    monkeypatch.setattr(settings, 'google_api_key', 'AIza-test-timeout')
    monkeypatch.setattr(settings, 'normalization_timeout_s', .01)
    agent_llm.reset_circuits()

    class Slow:
        def with_structured_output(self, *args, **kwargs):
            return self

        async def ainvoke(self, messages):
            await asyncio.sleep(1)

    monkeypatch.setattr(llm, 'get_normalization_llm', Slow)
    budget = {'deadline': time.monotonic() + 5, 'attempts': 0}
    result = await normalize_message('kh muon doi xe', recent_turns=[], budget=budget)
    assert result.needs_confirmation
    assert budget['attempts'] == 0
    assert budget['normalization_attempts'] == 1


@pytest.mark.parametrize('text', ['VF8 k phanh dc', 'VF8 K phanh dc'])
def test_model_suffix_is_not_mistaken_for_numeric_unit(text):
    assert evaluate_hard_safety(text)[1] == 'BRAKE_FAILURE'


@pytest.mark.asyncio
async def test_uppercase_shorthand_is_contextual_but_currency_is_protected(monkeypatch):
    from src.services.chat_normalization import normalize_message
    calls = []

    async def generate(state, prompt, schema):
        calls.append(state)
        return schema(expansions=[{'token': 'BH', 'replacement': 'bảo hành'}], needs_confirmation=False)

    monkeypatch.setattr('src.services.agent_llm.structured_call', generate)
    result = await normalize_message('BH pin VF8', recent_turns=[], budget={})
    assert result.text == 'bảo hành pin VF8'
    assert not result.needs_confirmation
    amount = await normalize_message('300 k', recent_turns=[], budget={})
    assert amount.text == '300 k'
    assert not amount.needs_confirmation
    assert len(calls) == 1


@pytest.mark.asyncio
async def test_google_model_requires_direct_key_or_gateway(monkeypatch):
    from src.config import get_settings
    from src.services import llm
    settings = get_settings()
    monkeypatch.setattr(settings, 'google_api_key', '')
    monkeypatch.setattr(settings, 'openai_api_key', 'sk-main-only')
    monkeypatch.setattr(settings, 'openai_base_url', '')
    monkeypatch.setattr(settings, 'normalization_model', 'gemini-2.5-flash-lite')
    with pytest.raises(ValueError, match='GOOGLE_API_KEY'):
        llm.get_normalization_llm()


def test_unicode_outside_vietnamese_does_not_shift_replacement_offsets():
    from src.services.chat_normalization import normalize_chat_text
    assert normalize_chat_text('Straße khong sac duoc CC01') == 'Straße không sạc được CC01'
