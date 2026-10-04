import asyncio
import json
import time

import pytest

from src.config import get_settings
from src.services import rag_service as module
from src.services.rag_service import RAGService


def test_missing_index_is_unavailable():
    out = RAGService().retrieve('bảo hành')
    assert out['status'] == 'UNAVAILABLE'
    assert out['diagnostics']['category'] == 'missing_index'


def backend_path():
    from pathlib import Path
    p = Path(get_settings().chroma_persist_dir)
    p.mkdir(parents=True, exist_ok=True)
    (p / 'chroma.sqlite3').touch()


def test_empty_collection_is_no_source(monkeypatch):
    backend_path()
    class Empty:
        def count(self):
            return 0
    monkeypatch.setattr(module, 'get_collection', lambda path: Empty())
    out = RAGService().retrieve('bảo hành')
    assert out['status'] == 'NO_SOURCE'
    assert out['diagnostics']['category'] == 'empty_collection'


def test_backend_exception_is_error_without_payload(monkeypatch):
    backend_path()
    def broken(path):
        raise RuntimeError('secret-query-and-password')
    monkeypatch.setattr(module, 'get_collection', broken)
    out = RAGService().retrieve('bảo hành')
    assert out['status'] == 'ERROR'
    assert out['citations'] == []
    assert 'secret-query-and-password' not in json.dumps(out)


def test_missing_collection_is_unavailable(monkeypatch):
    from chromadb.errors import NotFoundError
    backend_path()
    def missing(path):
        raise NotFoundError('missing collection')
    monkeypatch.setattr(module, 'get_collection', missing)
    assert RAGService().retrieve('bảo hành')['status'] == 'UNAVAILABLE'


@pytest.mark.asyncio
@pytest.mark.parametrize('query_size', [450, 6000])
async def test_prompt_overflow_escalates_with_category(monkeypatch, query_size):
    from src.agents.nodes import rag_node as node
    source = module.source_registry()['SRC-002']
    text = 'Thông tin chính thức. ' * 140
    async def found(*a, **k):
        return {'status': 'SUCCESS', 'citations': [{**source, 'source_id': 'SRC-002', 'applicable_models': ['ALL'],
                'relevant_snippet': text, 'distance': .2}], 'diagnostics': {'category': 'success'}}
    monkeypatch.setattr(node, 'vinfast_manual_search', found)
    query = 'câu hỏi tiếng Việt ' * query_size
    out = await node.rag_node({'latest_user_message': query, 'confidence_score': .9})
    assert out['rag_citations'] == []
    assert out['needs_staff_review']
    assert out['retrieval_diagnostics']['category'] == 'context_budget_exceeded'


@pytest.mark.asyncio
async def test_timeout_has_distinct_category(monkeypatch):
    from src.agents.nodes import rag_node as node
    async def slow(*a, **k):
        await asyncio.sleep(.1)
    monkeypatch.setattr(node, 'vinfast_manual_search', slow)
    out = await node.rag_node({'latest_user_message': 'bảo hành', 'llm_budget': {'deadline': time.monotonic() + .001}})
    assert out['retrieval_status'] == 'TIMEOUT'
    assert out['retrieval_diagnostics']['category'] == 'timeout'
    assert out['needs_staff_review'] and out['is_no_source']


@pytest.mark.asyncio
async def test_unavailable_reply_does_not_claim_missing_documents(monkeypatch):
    from src.agents.nodes import rag_node as node
    async def unavailable(*a, **k):
        return {'status': 'UNAVAILABLE', 'citations': [], 'diagnostics': {'category': 'missing_index'}}
    monkeypatch.setattr(node, 'vinfast_manual_search', unavailable)
    out = await node.rag_node({'latest_user_message': 'bảo hành'})
    assert 'tra cứu' in out['response']
    assert 'chưa có tài liệu' not in out['response']
    assert out['rag_citations'] == []
