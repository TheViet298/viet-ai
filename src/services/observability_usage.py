"""Provider usage normalization and direct-SDK generation ownership."""
from __future__ import annotations

from typing import Any
from src.services.observability import observation, update_observation


def _counts(value: Any, mapping: dict) -> dict[str, int] | None:
    if value is None:
        return None
    if hasattr(value, 'model_dump'):
        value = value.model_dump()
    if not isinstance(value, dict):
        return None
    result = {}
    for source, target in mapping.items():
        count = value.get(source)
        if isinstance(count, int) and not isinstance(count, bool) and count >= 0:
            result[target] = count
    return result or None


def normalize_openai_usage(usage: Any) -> dict[str, int] | None:
    result = _counts(usage, {'prompt_tokens': 'input', 'completion_tokens': 'output', 'total_tokens': 'total'})
    value = usage.model_dump() if hasattr(usage, 'model_dump') else usage
    if result is not None and isinstance(value, dict):
        result.update(_counts(value.get('prompt_tokens_details'), {'cached_tokens': 'input_cached_tokens'}) or {})
        result.update(_counts(value.get('completion_tokens_details'), {'reasoning_tokens': 'output_reasoning_tokens'}) or {})
    return result


def normalize_google_usage(usage: dict | None) -> dict[str, int] | None:
    return _counts(usage, {'promptTokenCount': 'input', 'candidatesTokenCount': 'output',
                           'totalTokenCount': 'total', 'cachedContentTokenCount': 'input_cached_tokens',
                           'thoughtsTokenCount': 'output_reasoning_tokens'})


async def provider_generation(name: str, provider: str, model: str, call, *, attempt: int = 1):
    with observation(name, as_type='generation', model=model,
                     metadata={'provider': provider, 'attempt': attempt}) as span:
        result = await call()
        if provider == 'google':
            body = result.json()
            usage = normalize_google_usage(body.get('usageMetadata'))
            failed = result.status_code >= 400
        else:
            usage = normalize_openai_usage(getattr(result, 'usage', None))
            failed = False
        fields = {'metadata': {'provider': provider, 'attempt': attempt,
                               'usage_status': 'reported' if usage is not None else 'missing'},
                  'status_message': 'provider_error' if failed else 'provider_completed',
                  'level': 'ERROR' if failed else 'DEFAULT'}
        if usage is not None:
            fields['usage_details'] = usage
        update_observation(span, **fields)
        return result
