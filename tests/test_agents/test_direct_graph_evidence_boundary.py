import pytest

from src.agents.nodes import general_node as general
from src.agents.nodes.triage_node import triage_node
from src.services.rag_service import requested_source_type


QUERIES = [
    'Hướng dẫn đăng nhập ứng dụng VinFast',
    'Cách điều khiển điều hòa từ xa trên app VinFast',
    'Cách xem lịch sử sạc trên ứng dụng VinFast',
    'Mobile Service VinFast hoạt động như thế nào?',
]


@pytest.mark.asyncio
@pytest.mark.parametrize('query', QUERIES)
async def test_graph_without_api_understanding_keeps_official_evidence_boundary(query, monkeypatch):
    state = {'latest_user_message': query, 'confidence_score': .9}
    triage = await triage_node(state)
    assert triage['is_rag_query']
    assert not triage['is_general_query']
    async def grounded(state):
        return {'response': 'grounded boundary'}
    from src.agents.nodes import rag_node
    monkeypatch.setattr(rag_node, 'rag_node', grounded)
    assert (await general.general_node(state))['response'] == 'grounded boundary'


def test_app_station_discovery_uses_app_guide_before_service_policy():
    assert requested_source_type('Cách tìm trạm sạc trên ứng dụng VinFast') == 'official_guide'
    # The registered Mobile Service instructions belong to the official app guide.
    assert requested_source_type('Mobile Service VinFast là gì?') == 'official_guide'

