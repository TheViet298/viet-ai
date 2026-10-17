from types import SimpleNamespace

import pytest
from pydantic import BaseModel

from src.config import get_settings
from src.services import observability as obs
from src.services.agent_llm import structured_call
from tests.test_observability import FakeClient


class Reply(BaseModel):
    answer: str


@pytest.mark.asyncio
async def test_memory_call_receives_explicit_callback_without_duplicating_graph(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, 'agent_llm_enabled', True)
    monkeypatch.setattr(settings, 'openai_api_key', 'test-fixture')
    monkeypatch.setattr(settings, 'model_name', 'gpt-4o-mini')
    calls = []

    class Chain:
        def with_structured_output(self, *args, **kwargs):
            return self

        async def ainvoke(self, messages, **kwargs):
            calls.append(kwargs)
            return {'raw': SimpleNamespace(usage_metadata={'input_tokens': 12, 'output_tokens': 5}),
                    'parsed': Reply(answer='ok')}

    monkeypatch.setattr('src.services.llm.get_llm', lambda: Chain())
    capture = FakeClient()
    monkeypatch.setattr(obs, '_client', capture)
    with obs.observation('root'):
        await structured_call({'session_id': 'graph'}, 'memory', Reply)
        await structured_call({'session_id': 'memory'}, 'memory', Reply, callbacks=['capture'])
    assert 'config' not in calls[0]
    assert calls[1]['config']['callbacks'] == ['capture']
    assert [r.fields['name'] for r in capture.records].count('llm.outcome') == 2
    assert all(r.fields.get('as_type') != 'generation' for r in capture.records)


@pytest.mark.asyncio
async def test_budget_exhausted_records_outcome_without_provider(monkeypatch):
    import time
    settings = get_settings()
    monkeypatch.setattr(settings, 'agent_llm_enabled', True)
    monkeypatch.setattr(settings, 'openai_api_key', 'test-fixture')
    capture = FakeClient()
    monkeypatch.setattr(obs, '_client', capture)
    with obs.observation('root'):
        result = await structured_call({'session_id': 'budget', 'llm_budget': {
            'attempts': 3, 'deadline': time.monotonic() + 10}}, 'memory', Reply)
    assert result is None
    outcomes = [r for r in capture.records if r.fields['name'] == 'llm.outcome']
    assert outcomes[0].fields['metadata']['outcome'] == 'budget_exhausted'
    assert 'usage_details' not in outcomes[0].fields
