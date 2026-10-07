from unittest.mock import patch

import pytest

from src.agents.nodes.intake_node import intake_node
from src.agents.nodes.triage_node import TriageResult, extract_fields, triage_node


@pytest.mark.parametrize('text', [
    'Tôi vẫn đang ở cạnh xe', 'Tôi đang ở đây', 'Tôi ở đó',
    'Tôi đứng ở bên cạnh xe', 'Tôi ở gần xe', 'Tôi ở một nơi an toàn',
    'Xe đang ở chế độ sạc', 'Xe ở trạng thái không sạc được',
    'Tôi ở trạm sạc', 'Tôi ở trạm sạc gần nhà',
    'Tôi ở trụ P01, mã lỗi CC01', 'Xe ở mức pin 20%',
])
def test_vague_or_non_location_text_cannot_become_location(text):
    fields = extract_fields(text)
    assert 'station_location' not in fields
    assert 'current_location' not in fields


@pytest.mark.parametrize(('text', 'expected'), [
    ('Xe VF8 không sạc được tại trạm Metropolis.', 'Metropolis'),
    ('Tôi đang ở trạm sạc Vincom Metropolis, cắm súng DC vào xe VF8.', 'Vincom Metropolis'),
    ('Xe không nhận sạc tại Vincom Metropolis', 'Vincom Metropolis'),
    ('Đính chính: tôi ở trạm sạc Vincom Landmark 81, trụ P02.', 'Vincom Landmark 81'),
    ('Trạm sạc Vincom Metropolis', 'Vincom Metropolis'),
    ('Xe không sạc được tại trạm Metropolis nhưng trụ vẫn sáng.', 'Metropolis'),
    ('Xe không sạc được ở nhà', 'Tại nhà'),
    ('VF8 không sạc được tại nhà lỗi E001', 'Tại nhà'),
])
def test_identified_charging_location_is_saved_without_following_clause(text, expected):
    assert extract_fields(text)['station_location'] == expected


def test_customer_address_is_not_assumed_to_be_charging_station():
    fields = extract_fields('Xe bốc khói, tôi đang ở đường Nguyễn Trãi')
    assert fields['current_location'] == 'đường Nguyễn Trãi'
    assert 'station_location' not in fields


@pytest.mark.asyncio
async def test_llm_cannot_turn_a_relative_position_into_a_station():
    proposed = TriageResult(intent='Charging/Battery', priority='MEDIUM', confidence_score=0.8,
                            captured_fields={'station_location': 'cạnh xe'})
    with patch('src.agents.nodes.triage_node.structured_call', return_value=proposed):
        result = await triage_node({'latest_user_message': 'Tôi ở cạnh xe'})
    assert 'station_location' not in result['captured_fields']


@pytest.mark.asyncio
async def test_core_charger_id_does_not_satisfy_station_location():
    from src.agents.chatbot_agent import process_chat_message
    from src.services.session_store import decode_state, get_store

    result = await process_chat_message('Xe VF8 không sạc được tại trụ P01, mã lỗi CC01',
                                        session_id='station-missing', user_role='customer', owner='c1')
    assert result['case_id'] is None
    assert result['response_type'] == 'CLARIFICATION'
    with get_store().connect() as db:
        state = decode_state(db.execute("SELECT state FROM agent_sessions WHERE id='station-missing'").fetchone()['state'])
    assert state['captured_fields']['charger_id'] == 'P01'
    assert 'station_location' not in state['captured_fields']


@pytest.mark.asyncio
async def test_ambiguous_followup_preserves_confirmed_station_then_valid_correction_updates_it():
    state = await intake_node({'latest_user_message': 'Xe VF8 không sạc được tại trạm Metropolis'})
    state['latest_user_message'] = 'Tôi vẫn đang ở cạnh xe'
    state = {**state, **await intake_node(state)}
    assert state['captured_fields']['station_location'] == 'Metropolis'
    state['latest_user_message'] = 'Đính chính: tôi ở trạm sạc Vincom Landmark 81'
    result = await intake_node(state)
    assert result['captured_fields']['station_location'] == 'Vincom Landmark 81'
    assert any(h['field'] == 'station_location' and h['value'] == 'Metropolis' and h['status'] != 'valid' for h in result['fact_history'])
