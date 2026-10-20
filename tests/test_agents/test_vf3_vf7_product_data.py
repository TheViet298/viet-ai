"""Source-scoped supplementation from the two requested official product pages."""
import json
from pathlib import Path
import pytest
from src.services.rag_service import RAGService
from src.services.vehicle_catalog import catalog_facts

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize('variant,minutes', [('eco',25),('plus',28),('plus-awd',37)])
def test_vf7_fast_charging_is_variant_specific(variant,minutes):
    fact = next(f for f in catalog_facts() if f['scope']['model']=='VF7' and f['scope']['variant']==variant)
    assert fact['card']['fast_charge_time'] == f'{minutes} phút'
    specs=[s for s in fact['card']['specs'] if s['label']=='Thời gian sạc']
    assert len(specs)==1, specs
    assert specs[0]['value']==f'{minutes} phút (từ 10%–70%)'
    assert f'{minutes} phút' in fact['claim_evidence']['fast_charge']['value']
    query = f"Thời gian sạc nhanh VF7 {variant.replace('-', ' ')} là bao lâu?"
    result = RAGService().retrieve(query, vehicle_model='VF7', source_need='catalog')
    assert result['status']=='SUCCESS',result
    text=' '.join(c['relevant_snippet'] for c in result['citations'])
    assert f'{minutes} phút' in text and '10%' in text and '70%' in text


@pytest.mark.asyncio
@pytest.mark.parametrize('question,model,terms', [
    ('VF3 có màu gì?', 'VF3', ['Rose Pink','Summer Yellow','Urban Mint']),
    ('VF3 Plus có màu gì?', 'VF3', ['Rose Pink','chưa','phiên bản']),
    ('VF7 Plus có màu gì?', 'VF7', ['tiêu chuẩn','nâng cao','Urban Mint']),
])
async def test_new_color_evidence_reaches_answers(question,model,terms,monkeypatch):
    from src.agents.nodes import rag_node as module
    async def search(query,**kwargs): return RAGService().retrieve(query,**kwargs)
    monkeypatch.setattr(module,'vinfast_manual_search',search)
    result=await module.rag_node({'latest_user_message':question,'vehicle_model':model,'confidence_score':.9})
    assert result['rag_citations'],result
    assert all(term.casefold() in result['response'].casefold()for term in terms),result
    assert 'tồn kho' not in result['response'].casefold(),result
    if 'Plus' in question:assert result['answer_status']=='partial'


def test_supplement_keeps_unresolved_scope_and_source_conflicts():
    snapshot=json.loads((ROOT/'fixtures/knowledge/source_reviews/vf3-vf7-product-2026-10-19.json').read_text(encoding='utf-8'))
    assert len(snapshot['models']['VF3']['exterior_colors'])==7
    assert snapshot['models']['VF7']['variants']['plus-awd']['fast_charge_minutes']==37
    assert snapshot['models']['VF7']['variants']['plus-awd']['price_vnd'] is None
    assert snapshot['models']['VF3']['model_specs']['usable_capacity_kwh']==18.64
    assert snapshot['models']['VF3']['variant_capacity_verified'] is False
    assert snapshot['source_conflicts']
    assert all(f['scope']['battery_capacity_kwh'] is None for f in catalog_facts() if f['scope']['model']=='VF3')



def test_new_color_sections_have_reviewed_english_without_rewriting_values():
    from src.services.help_localization import english_help_answer
    rows=json.loads((ROOT/'fixtures/knowledge/answer_gap_sections.json').read_text(encoding='utf-8'))
    for row in rows:
        if row['key'] not in {'vf3_model_colors','vf7_model_colors'}:continue
        translated=english_help_answer('Theo tài liệu VinFast:\n\n'+row['relevant_snippet'])
        assert translated and 'stock' not in translated.casefold()
        assert 'Urban Mint' in translated
