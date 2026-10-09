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
        result.update(_counts(value.get('prompt_tokens_details'), {'cached_tokens': 'input_cache_read'}) or {})
        result.update(_counts(value.get('completion_tokens_details'), {'reasoning_tokens': 'output_reasoning'}) or {})
        for parent, detail in [('input', 'input_cache_read'), ('output', 'output_reasoning')]:
            if parent in result and detail in result:
                result[parent] = max(0, result[parent] - result[detail])
    return result


def normalize_google_usage(usage: dict | None) -> dict[str, int] | None:
    result = _counts(usage, {'promptTokenCount': 'input', 'candidatesTokenCount': 'output',
                           'totalTokenCount': 'total', 'cachedContentTokenCount': 'input_cache_read',
                           'thoughtsTokenCount': 'output_reasoning'})
    if result and 'input' in result and 'input_cache_read' in result:
        result['input'] = max(0, result['input'] - result['input_cache_read'])
    return result


async def provider_generation(name: str, provider: str, model: str, call, *, attempt: int = 1):
    with observation(name, as_type='generation', model=model,
                     metadata={'provider': provider, 'attempt': attempt}) as span:
        result = await call()
        if provider == 'google':
            try:
                body = result.json()
            except (ValueError, TypeError):
                body = {}
            if not isinstance(body, dict):
                body = {}
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
