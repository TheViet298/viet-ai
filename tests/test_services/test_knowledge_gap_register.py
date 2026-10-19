import json
from pathlib import Path

from src.services.rag_service import source_registry


def test_gap_register_keeps_scope_and_honest_acquisition_state():
    root = Path(__file__).resolve().parents[2]
    registry = json.loads((root / 'data/verified/knowledge_gap_register.json').read_text(encoding='utf-8'))
    gaps = registry['gaps']
    assert len({gap['id'] for gap in gaps}) == len(gaps) == 20
    for gap in gaps:
        assert {'model', 'variant', 'year', 'topic', 'required_scope', 'status',
                'source_id', 'evidence_location', 'blocker', 'reviewer', 'reviewed_at'} <= gap.keys()
        assert gap['status'] in {'missing', 'acquired', 'pending_review', 'verified', 'partial', 'blocked'}
        if gap['source_id']:
            assert gap['source_id'] in source_registry()
        if gap['status'] in {'verified', 'partial'}:
            assert gap['reviewer'] and gap['reviewed_at'] and gap['evidence_location']
        if gap['status'] in {'blocked', 'partial'}:
            assert gap['blocker']
    vf3_capacity = next(gap for gap in gaps if gap['model'] == 'VF3' and gap['topic'] == 'battery_capacity')
    assert vf3_capacity['status'] == 'blocked'
    assert 'Philippines' in vf3_capacity['blocker']
