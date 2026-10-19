import numpy as np

from src.config import get_settings
from src.services import rag_service as module


def test_other_models_cannot_fill_twenty_candidate_slots(monkeypatch, tmp_path):
    from src.services import reviewed_gap_answers
    monkeypatch.setattr(reviewed_gap_answers, 'reviewed_gap_answers', lambda *args: [])
    (tmp_path / 'chroma.sqlite3').touch()
    monkeypatch.setattr(get_settings(), 'chroma_persist_dir', str(tmp_path))
    meta = {**module.source_registry()['SRC-002'], 'source_id': 'SRC-002'}

    class Embed:
        def embed_query(self, input):
            return [np.array([0.0, 0.0])]

    class Collection:
        configuration = {'hnsw': {'space': 'l2'}, 'embedding_function': Embed()}

        def count(self):
            return 21

    corpus = {'documents': ['VF8 bảo hành 10 năm hoặc 200000 km.'] * 21, 'metadatas': [{**meta, 'applicable_models': 'VF5'}] * 20 + [{**meta, 'applicable_models': 'VF8'}], 'embeddings': [np.array([0.1, 0.0])] * 20 + [np.array([0.5, 0.0])], 'ids': [f'wrong-{i}' for i in range(20)] + ['correct']}
    monkeypatch.setattr(module, 'get_collection', lambda path: Collection())
    monkeypatch.setattr(module, 'get_corpus', lambda *a: corpus)
    out = module.RAGService().retrieve('Bảo hành VF8 bao lâu?', vehicle_model='VF8')
    assert out['status'] == 'SUCCESS'
    assert out['citations'][0]['chunk_id'] == 'correct'


def test_same_count_update_invalidates_corpus_cache(monkeypatch, tmp_path):
    database = tmp_path / 'chroma.sqlite3'
    database.write_bytes(b'old')
    calls = []

    class Collection:
        def get(self, **kwargs):
            calls.append(1)
            return {'documents': [database.read_bytes().decode()]}

    monkeypatch.setattr(module, 'get_collection', lambda path: Collection())
    assert module.get_corpus(str(tmp_path), 1)['documents'] == ['old']
    database.write_bytes(b'changed')
    assert module.get_corpus(str(tmp_path), 1)['documents'] == ['changed']
    assert len(calls) == 2
