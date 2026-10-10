from unittest.mock import patch

import pytest

from src.agents.chatbot_agent import process_chat_message
from src.agents.context_manager import apply_fact_recency_and_invalidation, build_7_layer_context, trim_context_layers
from src.agents.nodes.intake_node import intake_node
from src.services.session_store import decode_state, get_store


@pytest.mark.asyncio
async def test_generated_summary_cannot_remove_compacted_evidence():
    from src.agents.chatbot_agent import MemorySummary
    marker = 'Liên hệ vào 17:30.'
    with patch('src.agents.chatbot_agent.structured_call', return_value=MemorySummary(summary='Trao đổi chung')):
        for i in range(6):
            await process_chat_message('Xin chào ' + 'chi tiết ' * 60 + marker if i == 0 else 'Xin chào',
                                       session_id='summary-evidence', user_role='customer', owner='c1', persist_business_case=False)
    with get_store().connect() as db:
        state = decode_state(db.execute("SELECT state FROM agent_sessions WHERE id='summary-evidence'").fetchone()['state'])
    assert any(marker in item['content'] and item['message_id'] for item in state.get('summary_evidence', []))


@pytest.mark.asyncio
async def test_lowercase_denial_retracts_uppercase_code():
    state = await intake_node({'latest_user_message': 'Xe VF8 của tôi đang báo lỗi CC01'})
    state['latest_user_message'] = 'Xe tôi không báo mã lỗi cc01'
    assert 'error_code' not in (await intake_node(state))['captured_fields']


@pytest.mark.asyncio
@pytest.mark.parametrize('text', ['Nếu xe VF5 khác báo lỗi CC02 thì làm gì?', 'Nếu xe không báo mã lỗi CC01 thì sao?'])
async def test_hypothetical_cannot_reset_or_retract_actual_incident(text):
    state = await intake_node({'latest_user_message': 'Xe VF8 của tôi đang báo lỗi CC01 tại trụ P01'})
    state['case_id'] = 'existing-case'
    state['latest_user_message'] = text
    result = await intake_node(state)
    assert result['captured_fields']['error_code'] == 'CC01'
    assert result['captured_fields']['vehicle_model'] == 'VF8'
    assert not result['vehicle_context']['scope_changed']


@pytest.mark.asyncio
async def test_vf_e34_different_vehicle_drops_old_error():
    state = await intake_node({'latest_user_message': 'Xe VF8 của tôi đang báo lỗi CC01 tại trụ P01'})
    state['latest_user_message'] = 'Tôi đang sử dụng xe VF e34 khác, xe này không sạc được'
    result = await intake_node(state)
    assert 'error_code' not in result['captured_fields']


@pytest.mark.asyncio
async def test_different_vehicle_clears_old_photo_evidence():
    state = {'latest_user_message': 'Tôi đang sử dụng xe VF5 khác, xe này không sạc được', 'turn': 2,
             'vehicle_context': {'owned_model': 'VF8', 'is_incident': True},
             'cardd_evidence': {'turn': 1, 'image_id': 'old-photo', 'status': 'detected', 'model_version': 'a' * 64,
                                'detections': [{'label': 'dent', 'confidence': 0.29,
                                                'bbox_xyxy': [0.1, 0.1, 0.8, 0.7]}],
                                'confirmation': 'confirmed', 'confirmation_turn': 2}}
    result = await intake_node(state)
    assert result['cardd_evidence'] is None


@pytest.mark.asyncio
async def test_core_new_vehicle_does_not_resummarize_old_messages():
    for _ in range(5):
        await process_chat_message('Xe VF8 của tôi đang báo lỗi CC01 tại trụ P01',
                                   session_id='scope-buffer', user_role='customer', owner='c1')
    await process_chat_message('Tôi đang sử dụng xe VF5 khác, xe này không sạc được',
                               session_id='scope-buffer', user_role='customer', owner='c1')
    with get_store().connect() as db:
        state = decode_state(db.execute("SELECT state FROM agent_sessions WHERE id='scope-buffer'").fetchone()['state'])
    assert 'CC01' not in state.get('memory_summary', '')
    assert all('CC01' not in str(m.content) for m in state['messages'])


@pytest.mark.asyncio
async def test_stale_dynamic_fact_is_not_used():
    result = await intake_node({'latest_user_message': 'Xin chào', 'captured_fields': {'current_soc': 18},
                               'fact_history': [{'field': 'current_soc', 'value': 18, 'status': 'valid',
                                                 'valid_from': '2020-01-01T00:00:00+00:00', 'valid_to': None}]})
    assert 'current_soc' not in result['captured_fields']
    assert result['fact_history'][0]['status'] == 'expired'


@pytest.mark.asyncio
async def test_core_different_vehicle_does_not_reuse_case():
    first = await process_chat_message('Xe VF8 của tôi không sạc được tại trạm Metropolis, trụ P01, mã lỗi CC01',
                                       session_id='core-cars', user_role='customer', owner='c1')
    assert first['case_id']
    await process_chat_message('Tôi đang sử dụng xe VF5 khác, xe này không sạc được',
                               session_id='core-cars', user_role='customer', owner='c1')
    brief = get_store().case(first['case_id'], 'c1')['case_brief']
    assert brief['captured_fields']['vehicle_model'] == 'VF8'
    with get_store().connect() as db:
        state = decode_state(db.execute("SELECT state FROM agent_sessions WHERE id='core-cars'").fetchone()['state'])
    assert state.get('case_id') != first['case_id']


@pytest.mark.asyncio
async def test_different_vehicle_drops_previous_incident_facts():
    state = await intake_node({'latest_user_message': 'Xe VF8 của tôi không sạc được tại trụ P01, mã lỗi CC01'})
    state['latest_user_message'] = 'Tôi đang sử dụng xe VF5 khác, xe này không sạc được'
    result = await intake_node(state)
    assert result['captured_fields'].get('vehicle_model') == 'VF5'
    assert not {'error_code', 'charger_id', 'station_location'} & result['captured_fields'].keys()
    assert all(h['status'] != 'valid' for h in result['fact_history'] if h['field'] == 'error_code')


@pytest.mark.asyncio
@pytest.mark.parametrize('text', ['Nếu xe VF8 báo lỗi CC01 ở trụ P01 thì làm gì?', 'Xe tôi không báo mã lỗi CC01'])
async def test_unasserted_error_not_saved_as_fact(text):
    result = await intake_node({'latest_user_message': text})
    assert 'error_code' not in result['captured_fields']
    assert not result['vehicle_context']['is_incident']


@pytest.mark.asyncio
async def test_denied_error_retracts_previous_fact():
    state = await intake_node({'latest_user_message': 'Xe VF8 của tôi đang báo lỗi CC01'})
    state['latest_user_message'] = 'Xe tôi không báo mã lỗi CC01 nữa'
    result = await intake_node(state)
    assert 'error_code' not in result['captured_fields']
    assert all(h['status'] != 'valid' for h in result['fact_history'] if h['field'] == 'error_code')


def test_retrieval_cannot_evict_current_fact():
    layers = build_7_layer_context({'latest_user_message': 'Kiểm tra xe', 'captured_fields': {'error_code': 'AUDIT_CC01_7F92'},
                                   'memory_summary': 'M' * 1800, 'rag_citations': [{'source_id': 'SOURCE', 'relevant_snippet': 'R' * 5100}]}, 'TASK_MARKER')
    messages = trim_context_layers(layers)
    text = '\n'.join(str(m.content) for m in messages)
    assert 'AUDIT_CC01_7F92' in text and 'TASK_MARKER' in text
    assert sum(len(str(m.content).encode('utf-8')) for m in messages) <= 8000


def test_same_fact_refreshes_observation_time():
    facts, history = apply_fact_recency_and_invalidation({}, [], 'current_soc', 18, 'user:turn:1')
    history[0]['last_seen_at'] = '2020-01-01T00:00:00+00:00'
    _, updated = apply_fact_recency_and_invalidation(facts, history, 'current_soc', 18, 'user:turn:100')
    assert updated[0]['last_seen_at'] != history[0]['last_seen_at']
    assert updated[0]['last_seen_provenance'] == 'user:turn:100'
    assert updated[0]['provenance'] == 'user:turn:1'


@pytest.mark.asyncio
async def test_compaction_keeps_long_message_tail():
    marker = 'Liên hệ vào 17:30.'
    for i in range(6):
        await process_chat_message('Xin chào ' + 'chi tiết ' * 60 + marker if i == 0 else 'Xin chào',
                                   session_id='tail', user_role='customer', owner='c1', persist_business_case=False)
    with get_store().connect() as db:
        state = decode_state(db.execute("SELECT state FROM agent_sessions WHERE id='tail'").fetchone()['state'])
    assert marker in state['memory_summary'] or any(marker in str(m.content) for m in state['messages'])


@pytest.mark.asyncio
async def test_failed_core_turn_does_not_consume_quota():
    with patch('src.agents.chatbot_agent.agent.ainvoke', side_effect=RuntimeError('injected')):
        with pytest.raises(RuntimeError):
            await process_chat_message('Xin chào', session_id='failure', owner='guest:failure', user_role='guest')
    with get_store().connect() as db:
        row = db.execute("SELECT guest_turns FROM agent_sessions WHERE id='failure'").fetchone()
        assert row['guest_turns'] == 0
