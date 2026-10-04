import json

import pytest

from src.agents.chatbot_agent import process_chat_message
from src.services.session_store import decode_state, get_store


@pytest.mark.asyncio
@pytest.mark.parametrize('original,corrected', [('VF8', 'VF5'), ('VF5', 'VF6'), ('VF6', 'VF7'), ('VF7', 'VF9')])
async def test_corrected_model_is_used_for_persisted_case(original, corrected):
    session = f'correction-{original}-{corrected}'
    first = await process_chat_message(f'Xe {original} bị hỏng', session_id=session, user_role='customer', owner='c1')
    second = await process_chat_message(f'Tôi nói nhầm, xe {corrected} không khởi động ở nhà', session_id=session, user_role='customer', owner='c1')
    assert second['needs_staff_review']
    third = await process_chat_message('Màn hình tối, xe không đi được', session_id=session, user_role='customer', owner='c1')
    assert third['case_brief']['vehicle_model'] == corrected
    assert third['case_id']
    with get_store().connect() as db:
        state = decode_state(db.execute('SELECT state FROM agent_sessions WHERE id=?', (session,)).fetchone()['state'])
        assert state['captured_fields']['vehicle_model'] == corrected
        assert 'llm_budget' not in state
        assert original in json.dumps(state['fact_history'], ensure_ascii=False)
    assert first['clarification_turn'] == 1
