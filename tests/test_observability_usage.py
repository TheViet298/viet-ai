from types import SimpleNamespace

import pytest
from src.services import observability as obs
from tests.test_observability import FakeClient


def test_provider_usage_is_not_estimated_or_double_counted():
    from src.services.observability_usage import normalize_openai_usage, normalize_google_usage
    assert normalize_openai_usage({'prompt_tokens': 12, 'completion_tokens': 5, 'total_tokens': 17}) == {
        'input': 12, 'output': 5, 'total': 17}
    assert normalize_google_usage({'promptTokenCount': 20, 'candidatesTokenCount': 7,
                                    'totalTokenCount': 27, 'cachedContentTokenCount': 4}) == {
        'input': 20, 'output': 7, 'total': 27, 'input_cached_tokens': 4}
    assert normalize_openai_usage(None) is None
    assert normalize_google_usage({'promptTokenCount': -3}) is None
    assert normalize_openai_usage({'prompt_tokens': 0, 'completion_tokens': 0, 'total_tokens': 0}) == {
        'input': 0, 'output': 0, 'total': 0}


@pytest.mark.asyncio
async def test_usage_survives_consumer_parse_failure(monkeypatch):
    from src.services.observability_usage import provider_generation
    capture = FakeClient()
    monkeypatch.setattr(obs, '_client', capture)

    async def call():
        return SimpleNamespace(usage={'prompt_tokens': 12, 'completion_tokens': 5, 'total_tokens': 17})

    with obs.validation_context('fixture-run', 'LF-06'):
        with obs.observation('root'):
            await provider_generation('vision.exterior', 'openai', 'actual-model', call)
            with pytest.raises(ValueError):
                raise ValueError('parse failed afterwards')
    generation = capture.records[1]
    assert generation.fields['usage_details'] == {'input': 12, 'output': 5, 'total': 17}
    assert generation.fields['model'] == 'actual-model'
    assert generation.fields['metadata']['run_id'] == 'fixture-run'
    assert 'cost_details' not in generation.fields


@pytest.mark.asyncio
async def test_timeout_generation_has_error_without_fake_zero_usage(monkeypatch):
    from src.services.observability_usage import provider_generation
    capture = FakeClient()
    monkeypatch.setattr(obs, '_client', capture)

    async def call():
        raise TimeoutError('sensitive provider fixture')

    with obs.observation('root'):
        with pytest.raises(TimeoutError):
            await provider_generation('vision.dashboard', 'google', 'actual-model', call)
    span = capture.records[1]
    assert span.fields['status_message'] == 'timeout'
    assert 'usage_details' not in span.fields
    assert 'sensitive provider fixture' not in str(span.fields)
