import pytest
from src.services.rag_service import RAGService, requested_source_type, valid_citation, source_registry
from src.services.conversation_context import TurnUnderstanding
from src.services.vehicle_catalog import select_vehicle_cards


@pytest.mark.parametrize('query,kind', [
    ('Hướng dẫn đăng nhập ứng dụng VF8 Plus', 'official_guide'),
    ('Hướng dẫn đặt lịch bảo dưỡng VF8 Plus', 'official_guide'),
    ('ADAS VF8 Plus hoạt động thế nào?', 'official_manual'),
    ('Bảo hành VF8 Plus', 'official_policy'),
])
def test_purpose_precedes_trim(query, kind):
    assert requested_source_type(query) == kind


def test_charging_cost_never_returns_purchase_snapshot():
    result = RAGService().retrieve('Giá sạc VF8 là bao nhiêu?', vehicle_model='VF8', cost_subject='charging')
    assert result.get('diagnostics', {}).get('category') != 'verified_public_price_snapshot'


def test_generic_pin_keyword_does_not_relax_distance():
    citation = {**source_registry()['SRC-002'], 'source_id': 'SRC-002', 'applicable_models': ['ALL'],
                'distance': 1.0, 'relevant_snippet': 'VinFast sạc pin.'}
    assert not valid_citation(citation, 'VF8')


def test_canonical_service_contract_denies_cards_despite_vehicle_keyword():
    turn = TurnUnderstanding(original_text='tư vấn vf8', resolved_query='Bảo hành VF8', goal='warranty', request_kind='faq')
    assert select_vehicle_cards('tư vấn vf8', understanding=turn) == []
