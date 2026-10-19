import json

import pytest


def test_candidate_records_keep_source_scope_and_no_inferred_vf3_capacity():
    from scripts.build_remediation_candidate import reviewed_records
    records = reviewed_records()
    assert len(records) == 5
    assert len({record['id'] for record in records}) == 5
    for record in records:
        scope = json.loads(record['metadata']['reviewed_scope_json'])
        assert scope['model_year'] is None and scope['variant'] is None
        assert record['metadata']['source_id'] in {'SRC-004', 'SRC-009'}
        assert record['metadata']['content_reviewed_at'] == '2026-10-19'
    assert not any('VF3' in record['document'] and 'kWh' in record['document'] for record in records)


def test_recover_parents_restores_header_and_rejects_tampering():
    from scripts.build_remediation_candidate import recover_parents
    from src.services.rag_index import content_hash
    parent = {'id': 'p1', 'document': 'Header\ncondition\nmodel row', 'metadata': {'source_id': 'SRC-004'}}
    parent['sha256'] = content_hash(parent)
    text = 'model row'
    corpus = {'ids': ['p1::child:0:' + content_hash(text)[:12]], 'documents': [text],
              'metadatas': [{'parent_chunk_id': 'p1', 'parent_sha256': parent['sha256']}]}
    assert recover_parents(corpus, {'p1': parent}) == [{key: parent[key] for key in ('id', 'document', 'metadata')}]
    corpus['documents'][0] = 'different row'
    with pytest.raises(ValueError, match='integrity'):
        recover_parents(corpus, {'p1': parent})
