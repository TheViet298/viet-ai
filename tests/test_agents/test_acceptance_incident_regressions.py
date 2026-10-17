import pytest

from src.agents.nodes.triage_node import classify_request_kind


CURRENT_REPORTS = [
    'Pin VF6 bị tụt mức sạc nhanh',
    'Tôi cần hỗ trợ trụ sạc VF8 không hoạt động',
    'Tôi phản hồi mức pin VF7 hiển thị sai',
]


@pytest.mark.parametrize('text', CURRENT_REPORTS + [
    'Pin VF6 bi tut muc sac nhanh',
    'Toi can ho tro tru sac VF8 khong hoat dong',
    'Toi phan hoi muc pin VF7 hien thi sai',
])
def test_current_battery_and_charger_reports_are_incidents(text):
    assert classify_request_kind(text) == 'incident'


@pytest.mark.parametrize('text', [
    'Pin VF6 không bị tụt mức sạc nhanh, tôi hỏi giá xe',
    'Trụ sạc VF8 không phải không hoạt động, tôi hỏi thông số',
    'Mức pin VF7 không hiển thị sai, tôi hỏi bảo hành',
    'Nếu pin VF6 bị tụt mức sạc nhanh thì làm gì?',
    'Giả sử trụ sạc VF8 không hoạt động thì làm gì?',
    'Nếu mức pin VF7 hiển thị sai thì làm sao?',
])
def test_denied_or_hypothetical_reports_do_not_create_incidents(text):
    assert classify_request_kind(text) == 'faq'


@pytest.mark.asyncio
@pytest.mark.parametrize('text', CURRENT_REPORTS)
async def test_current_battery_and_charger_reports_require_graph_staff_review(text):
    from src.agents.graph import agent

    result = await agent.ainvoke({'query': text, 'user_role': 'customer'})
    assert result['routing'] == 'charging_support'
    assert result['needs_staff_review'] is True
    assert not result['is_general_query']
    assert not result['is_critical']
