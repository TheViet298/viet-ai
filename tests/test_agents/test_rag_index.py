import json
from types import SimpleNamespace

import pytest

from src.services.rag_service import RAGService, source_registry


class CharacterTokenizer:
    """Small deterministic boundary fixture; prefix and special tokens count."""
    def encode(self, text):
        return SimpleNamespace(ids=[0] + list(text) + [1])


def record(text='Thông tin bảo hành chính thức đầy đủ cho xe VF8. ' * 10):
    return {'id': 'p1', 'document': text, 'metadata': {
        **source_registry()['SRC-002'], 'source_id': 'SRC-002', 'applicable_models': 'VF8'}}


def test_children_fit_256_with_prefix():
    from src.services.rag_index import split_passage
    parts = split_passage(record()['document'], CharacterTokenizer())
    assert len(parts) > 1
    assert all(len(CharacterTokenizer().encode('passage: ' + p).ids) <= 256 for p in parts)


def test_unbroken_text_preserves_content():
    from src.services.rag_index import split_passage
    text = 'ắ' * 1000 + '\n Cuối tài liệu.'
    assert ''.join(split_passage(text, CharacterTokenizer())) == text


def test_parent_retains_full_procedure():
    from src.services.rag_index import make_child_records
    original = record('Bước 1: chọn mục.\n' * 50 + 'Chỉ khi đủ điều kiện.')
    children, parents = make_child_records([original], CharacterTokenizer())
    assert parents['p1']['document'] == original['document']
    assert len(children) > 1
    assert {c['metadata']['parent_chunk_id'] for c in children} == {'p1'}


def test_duplicate_children_return_one_parent():
    from src.services.rag_index import make_child_records
    parent = record()
    records, parents = make_child_records([parent], CharacterTokenizer())
    children = {'documents': [[c['document'] for c in records]], 'metadatas': [[c['metadata'] for c in records]],
                'distances': [[.2] * len(records)], 'ids': [[c['id'] for c in records]]}
    out = RAGService().filter_results(children, 'VF8', 'bảo hành', parent_map=parents)
    assert len(out['citations']) == 1
    assert out['citations'][0]['parent_chunk_id'] == 'p1'
    assert out['citations'][0]['distance'] == .2
    assert out['citations'][0]['relevant_snippet'] == parent['document']


def test_parent_model_variant_checks_remain():
    from src.services.rag_index import make_child_records
    parent = record('Thông số xe VF5 Plus dung lượng pin 99 kWh chính thức.')
    parent['metadata']['applicable_models'] = 'VF5'
    children, parents = make_child_records([parent], CharacterTokenizer())
    result = {'documents': [[children[0]['document']]], 'metadatas': [[children[0]['metadata']]], 'distances': [[.1]], 'ids': [[children[0]['id']]]}
    out = RAGService().filter_results(result, 'VF8', 'Eco dung lượng', parent_map=parents)
    assert out['citations'] == []


def test_corrupt_mapping_fails_closed(tmp_path):
    from src.services.rag_index import load_parent_map
    (tmp_path / 'parent-map.json').write_text(json.dumps({'p1': record()}), encoding='utf-8')
    with pytest.raises(ValueError):
        load_parent_map(str(tmp_path))


def test_child_parent_hash_mismatch_fails_closed():
    from src.services.rag_index import make_child_records
    children, parents = make_child_records([record()], CharacterTokenizer())
    children[0]['metadata']['parent_sha256'] = '0' * 64
    result = {'documents': [[children[0]['document']]], 'metadatas': [[children[0]['metadata']]],
              'distances': [[.1]], 'ids': [[children[0]['id']]]}
    with pytest.raises(ValueError, match='integrity'):
        RAGService().filter_results(result, 'VF8', parent_map=parents)


def test_build_refuses_active_or_nonempty_target(tmp_path):
    from scripts.build_rag_candidate import validate_target
    with pytest.raises(ValueError):
        validate_target(tmp_path, tmp_path)
    target = tmp_path / 'candidate'
    target.mkdir()
    (target / 'existing').touch()
    with pytest.raises(ValueError):
        validate_target(tmp_path, target)
