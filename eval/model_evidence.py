"""Record real provider responses at evaluation boundaries, without saving prompts or secrets."""
from __future__ import annotations

import importlib
import re
import sys
from contextlib import ExitStack, contextmanager
from contextvars import ContextVar
from unittest.mock import patch
from uuid import uuid4

_call = ContextVar('golden_model_call', default=('', ''))


def model_matches(requested, actual):
    if not isinstance(actual, str):
        return False
    requested, actual = requested.removeprefix('models/'), actual.removeprefix('models/')
    return actual == requested or bool(re.fullmatch(re.escape(requested) + r'-\d{4}-\d{2}-\d{2}', actual))


def verify_calls(rows, required, *, forbid_calls=False):
    failures = []
    if forbid_calls and rows:
        failures.append('forbidden_model_call')
    for requirement in required:
        matches = [r for r in rows if r.get('phase') == requirement['phase']
                   and r.get('requested_model') == requirement['model']]
        good = [r for r in matches if r.get('success') and r.get('parsed')
                and model_matches(requirement['model'], r.get('actual_model'))
                and isinstance(r.get('total_tokens'), int) and not isinstance(r.get('total_tokens'), bool)
                and r['total_tokens'] > 0]
        if not good:
            failures.append(f"model_evidence_missing:{requirement['phase']}:{requirement['model']}")
    return failures


class RecordedModel:
    def __init__(self, runnable, model, rows):
        self.runnable, self.model, self.rows = runnable, model, rows

    def with_structured_output(self, *args, **kwargs):
        return RecordedModel(self.runnable.with_structured_output(*args, **kwargs), self.model, self.rows)

    async def ainvoke(self, *args, **kwargs):
        phase, call_id = _call.get()
        record = {'phase': phase, 'call_id': call_id, 'requested_model': self.model,
                  'actual_model': None, 'total_tokens': None, 'success': False, 'parsed': False}
        self.rows.append(record)
        try:
            result = await self.runnable.ainvoke(*args, **kwargs)
            raw = result.get('raw') if isinstance(result, dict) else result
            metadata = getattr(raw, 'response_metadata', None) or {}
            usage = getattr(raw, 'usage_metadata', None) or {}
            record.update(actual_model=metadata.get('model_name') or metadata.get('model') or metadata.get('model_version'),
                          total_tokens=usage.get('total_tokens'), success=True)
            return result
        except Exception as error:
            from src.services.agent_llm import classify_provider_error
            record['outcome'] = classify_provider_error(error)
            record['error_type'] = type(error).__name__
            code = getattr(error, 'status_code', None) or getattr(error, 'code', None)
            if isinstance(code, int):
                record['http_status'] = code
            body = getattr(error, 'body', None)
            if isinstance(body, dict):
                details = body.get('error', body)
                if isinstance(details, dict):
                    for key in ('code', 'type', 'param'):
                        value = details.get(key)
                        if isinstance(value, str) and re.fullmatch(r'[A-Za-z0-9_.\[\]-]{1,100}', value):
                            record['provider_' + key] = value
            raise


@contextmanager
def record_model_calls(rows):
    """Transparent wrappers: requests, prompts and parsed results still use production code."""
    from src.config import get_settings
    from src.services import agent_llm, llm
    settings = get_settings()
    original = agent_llm.structured_call

    async def structured(state, prompt, schema, **kwargs):
        call_id = uuid4().hex
        token = _call.set((prompt, call_id))
        try:
            result = await original(state, prompt, schema, **kwargs)
            for row in rows:
                if row.get('call_id') == call_id:
                    row['parsed'] = isinstance(result, schema)
            return result
        finally:
            _call.reset(token)

    normal, main = llm.get_normalization_llm, llm.get_llm
    names = ['src.agents.chatbot_agent', 'src.agents.nodes.general_node', 'src.agents.nodes.rag_node',
             'src.agents.nodes.triage_node', 'src.services.customer_localization',
             'src.services.chat_normalization', 'src.services.conversation_context']
    for name in names:
        importlib.import_module(name)
    with ExitStack() as stack:
        for module in list(sys.modules.values()):
            if getattr(module, '__name__', '').startswith('src.') and getattr(module, 'structured_call', None) is original:
                stack.enter_context(patch.object(module, 'structured_call', structured))
        stack.enter_context(patch.object(llm, 'get_llm', lambda: RecordedModel(main(), settings.model_name, rows)))
        stack.enter_context(patch.object(llm, 'get_normalization_llm',
                                        lambda: RecordedModel(normal(), settings.normalization_model, rows)))
        for name in ['image_routing', 'dashboard_vision_service', 'vehicle_vision_service']:
            module = importlib.import_module('src.services.' + name)
            provider = module.provider_generation

            async def tracked(name, vendor, model, call, *, attempt=1, _provider=provider):
                from src.services.agent_llm import classify_provider_error
                from src.services.observability_usage import normalize_google_usage, normalize_openai_usage
                record = {'phase': name, 'requested_model': model, 'actual_model': None,
                          'total_tokens': None, 'success': False, 'parsed': False}
                rows.append(record)
                try:
                    result = await _provider(name, vendor, model, call, attempt=attempt)
                    if vendor == 'google':
                        body = result.json()
                        usage = normalize_google_usage(body.get('usageMetadata')) or {}
                        actual = body.get('modelVersion')
                        success = result.status_code == 200
                    else:
                        usage = normalize_openai_usage(getattr(result, 'usage', None)) or {}
                        actual, success = getattr(result, 'model', None), True
                    record.update(actual_model=actual, total_tokens=usage.get('total'), success=success)
                    return result
                except Exception as error:
                    record['outcome'] = classify_provider_error(error)
                    raise

            stack.enter_context(patch.object(module, 'provider_generation', tracked))
        yield
