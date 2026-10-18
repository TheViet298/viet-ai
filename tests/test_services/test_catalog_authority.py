import pytest
from src.services.vehicle_catalog import select_vehicle_cards
from scripts.audit_knowledge_coverage import coverage_rows


def test_each_card_has_same_scoped_quote_fact():
    from src.services.vehicle_catalog import public_price_snapshots, catalog_citations
    cards = select_vehicle_cards('Tư vấn xe VF7')
    prices = public_price_snapshots()
    for card in cards:
        row = next(r for r in prices if r['model'] == card.model and r['variant'] == card.variant)
        assert row['price_type'] == 'list'
        assert row['drivetrain'] == ('AWD' if card.variant == 'plus-awd' else 'FWD')
        assert row['model_year'] is None
        assert row['market'] == 'VN'
        assert row['source_section']
        if card.variant == 'plus-awd':
            assert row['price_vnd'] is None
        else:
            assert f"{row['price_vnd']:,}".replace(',', '.') in card.price_label
    evidence = catalog_citations(cards)
    assert all(c['fact_scope']['variant'] for c in evidence)
    assert any('150 kW' in c['relevant_snippet'] for c in evidence)
    assert any('260 kW' in c['relevant_snippet'] for c in evidence)


def test_legacy_rankings_do_not_claim_cross_standard_winner():
    from src.services.knowledge_questions import format_lineup_ranking
    reply, citations, _ = format_lineup_ranking('range')
    assert 'xa nhất hiện nay' not in reply
    assert '635 km (NEDC)' in reply
    assert '626 km (WLTP)' in reply
    assert all(c['source_type'] == 'official_catalog' and c.get('fact_scope') for c in citations)


def test_service_coverage_and_model_specific_trim_applicability():
    reg = {'s': {'source_type': 'official_service', 'verified_at': '2026-10-15', 'applicable_models': ['VF5']}}
    rows = coverage_rows([{'source_id': 's'}], ['VF5 bảo dưỡng và trạm sạc'], reg)
    assert not any(r['model'] == 'VF5' and r['trim'] in {'Eco', 'Plus'} for r in rows)
    assert next(r for r in rows if r['model'] == 'VF5' and r['domain'] == 'maintenance')['status'] == 'available'
    assert next(r for r in rows if r['model'] == 'VF5' and r['domain'] == 'charging_network')['status'] == 'available'


def test_public_hub_has_no_unreviewed_repair_or_blanket_policy_claims():
    from src.api.public import VERIFIED_ARTICLES, SUPPORT_INSIGHTS
    text = ' '.join(a.content for a in VERIFIED_ARTICLES) + ' '.join(i.recommended_action for i in SUPPORT_INSIGHTS)
    for unsupported in ['CC01 (lỗi giao tiếp BMS)', 'chờ 30 giây', '12.000km', '5 phút', '2.5mm', 'pack pin miễn phí']:
        assert unsupported not in text

def test_card_price_expires_with_quote_review_window(monkeypatch):
    from datetime import date
    from src.services import vehicle_catalog
    class Later(date):
        @classmethod
        def today(cls):
            return cls(2026, 10, 24)
    monkeypatch.setattr(vehicle_catalog, 'date', Later)
    assert all(c.price_label == 'Chưa có giá xác thực' for c in vehicle_catalog.catalog_cards())


def test_catalog_price_claim_has_its_own_review_metadata():
    from src.services.vehicle_catalog import catalog_cards, catalog_citations
    card = catalog_cards(['VF7'])[1]
    evidence = catalog_citations([card])[0]
    assert '830.000.000 VNĐ' in evidence['relevant_snippet']
    assert evidence['price_evidence']['reviewed_at'] == '2026-10-16'

def test_card_price_is_rendered_from_canonical_price_fact(monkeypatch):
    from copy import deepcopy
    from src.services import vehicle_catalog
    facts = deepcopy(vehicle_catalog.catalog_facts())
    facts[0]['price']['price_vnd'] = 123000000
    monkeypatch.setattr(vehicle_catalog, 'catalog_facts', lambda: facts)
    assert vehicle_catalog.catalog_cards()[0].price_label == 'Từ 123.000.000 VNĐ'

def test_legacy_comparison_keeps_explicit_trim_qualifiers():
    from src.services.knowledge_questions import format_vehicle_comparison
    reply = format_vehicle_comparison(['VF7', 'VF8'], 'VF7 Plus AWD và VF8 Eco khác nhau ở đâu?')
    assert 'VF 7 Plus AWD' in reply
    assert '260 kW' in reply
    assert '469 km (NEDC)' in reply
    assert 'VF 8 Eco' in reply
    assert '500,5 km' not in reply

def test_legacy_comparison_does_not_drop_third_model():
    from src.services.knowledge_questions import format_vehicle_comparison
    reply = format_vehicle_comparison(['VF3', 'VF6', 'VF9'])
    assert all(name in reply for name in ['VF 3 Eco', 'VF 6 Eco', 'VF 9 Eco'])

@pytest.mark.asyncio
async def test_multitopic_overview_keeps_each_variant_evidence(monkeypatch):
    from src.services import knowledge_questions as module
    from src.services.vehicle_catalog import catalog_cards
    async def missing(state):
        return {'response': 'Chưa có tài liệu', 'rag_citations': [], 'is_no_source': True}
    monkeypatch.setattr(module, 'rag_node', missing)
    result = await module.answer_sales_question('Tư vấn các dòng xe và giá lăn bánh', None, 'scoped-overview')
    scopes = {(c['fact_scope']['model'], c['fact_scope']['variant']) for c in result['citations']}
    assert scopes == {(c.model, c.variant) for c in catalog_cards()}
    assert not result['is_no_source']


def test_verified_color_names_have_explicit_list_boundaries():
    from src.services.vehicle_catalog import format_catalog_color_reply
    names = 'Infinity Blanc Jet Black Crimson Red Ivy Green'
    source = f'Màu sắc ngoại thất được giới thiệu cho dòng VinFast VF 8: {names}.\nChưa xác nhận màu có sẵn cho từng phiên bản.'
    citation = {'source_id': 'SRC-009', 'url': 'https://vinfastauto.com/vn_vi/dat-coc-xe-vf8',
                'catalog_scope': 'model_colors', 'applicable_models': ['VF8'], 'relevant_snippet': source}
    reply = format_catalog_color_reply(source, [citation])
    assert 'Infinity Blanc; Jet Black; Crimson Red; Ivy Green.' in reply
    assert 'Chưa xác nhận màu có sẵn cho từng phiên bản.' in reply
    assert citation['relevant_snippet'] == source


def test_color_formatting_never_guesses_unknown_or_unverified_boundaries():
    from src.services.vehicle_catalog import format_catalog_color_reply
    text = 'VF8: Infinity Blanc Jet Black Crimson Red Ivy Green.'
    assert format_catalog_color_reply(text, []) == text
    assert format_catalog_color_reply(text, [{'source_id': 'SRC-009', 'url': 'https://example.com',
                                             'catalog_scope': 'model_colors', 'relevant_snippet': text}]) == text
    unknown = 'VF8: Blue Ocean White Pearl.'
    assert format_catalog_color_reply(unknown, [{'source_id': 'SRC-009', 'url': 'https://vinfastauto.com/vn_vi/dat-coc-xe-vf8',
                                               'catalog_scope': 'model_colors', 'relevant_snippet': unknown}]) == unknown
