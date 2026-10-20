"""Product supplementation must preserve generation and source boundaries."""
import json
from pathlib import Path

import pytest

from src.services.rag_service import RAGService
from src.services.vehicle_catalog import catalog_facts

ROOT = Path(__file__).resolve().parents[2]
REVIEW = ROOT / 'fixtures/knowledge/source_reviews/vf5-vf6-vf8-vf9-product-2026-10-19.json'


def test_five_product_snapshots_keep_generations_and_conflicts_separate():
    data = json.loads(REVIEW.read_text(encoding='utf-8'))
    assert set(data['models']) == {'VF5', 'VF6', 'VF8', 'VF8_THE_ALL_NEW_2026', 'VF9'}
    new = data['models']['VF8_THE_ALL_NEW_2026']
    assert new['variants'] == {}
    assert new['model_specs']['usable_capacity_kwh'] == 60.13
    assert new['model_specs']['fast_charge']['operator'] == '<'
    assert new['model_specs']['fast_charge']['station_kw'] == 250
    assert new['runtime_status'] == 'archived_separate_generation'
    assert data['models']['VF8']['variants']['eco']['range_km'] == 635
    assert data['models']['VF8']['variants']['plus']['range_km'] == 475
    assert data['models']['VF9']['variants']['plus']['range_standard'] == 'WLTP'
    assert data['models']['VF5']['model_specs']['dc_max_kw']['approximate'] is True
    assert len(data['source_conflicts']) >= 4
    assert all(r['status'] == 200 and len(r['sha256']) == 64 for r in data['acquisition'])


@pytest.mark.parametrize('model,colors', [
    ('VF6', ['Infinity Blanc', 'Zenith Grey', 'Jet Black', 'Urban Mint', 'Solar Ruby']),
    ('VF8', ['Infinity Blanc', 'Jet Black', 'Crimson Red', 'Ivy Green']),
    ('VF9', ['Infinity Blanc', 'Zenith Grey', 'Jet Black', 'Urban Mint', 'Crimson Red', 'Ivy Green', 'Desat Silver']),
])
def test_new_palette_evidence_is_retrievable_and_translatable(model, colors):
    from src.services.help_localization import english_help_answer
    result = RAGService().retrieve(f'{model} có màu gì?', vehicle_model=model, source_need='catalog')
    assert result['status'] == 'SUCCESS', result
    text = '\n'.join(c['relevant_snippet'] for c in result['citations'])
    assert all(color in text for color in colors), text
    assert 'tồn kho' not in text and 'đời xe' in text
    english = english_help_answer('Theo tài liệu VinFast:\n\n' + text)
    assert english and 'stock' not in english and all(color in english for color in colors)
    assert all(c['source_id'] == 'SRC-009' for c in result['citations'])


def test_new_generation_does_not_overwrite_legacy_catalog():
    legacy = [f for f in catalog_facts() if f['scope']['model'] == 'VF8']
    assert len(legacy) == 2
    assert all(f['scope']['battery_capacity_kwh'] == 87.7 for f in legacy)
    from src.services.reviewed_gap_answers import reviewed_gap_answers
    for query in ['VF8 The All New có màu gì?', 'VF8 all-new có màu gì?', 'VF8 2026 có màu gì?', 'VF8 thế hệ mới có màu gì?']:
        assert not reviewed_gap_answers(query, 'VF8')


def test_missing_color_gaps_are_only_partially_resolved():
    data = json.loads((ROOT / 'data/verified/knowledge_gap_register.json').read_text(encoding='utf-8'))
    for model in ['VF6', 'VF9']:
        gap = next(g for g in data['gaps'] if g['model'] == model and g['topic'] == 'colors')
        assert gap['status'] == 'partial'
        assert gap['evidence_location'].endswith(REVIEW.name)
