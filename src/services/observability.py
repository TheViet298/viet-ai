"""Fail-open Langfuse contexts; business decisions remain with callers."""
from __future__ import annotations

import asyncio
import functools
import inspect
import os
import re
import time
from contextlib import contextmanager, nullcontext
from contextvars import ContextVar
from hashlib import sha256
from pathlib import Path
from typing import Any

_client: Any = None
_root: ContextVar[Any] = ContextVar('lf_root', default=None)
_identity: ContextVar[dict] = ContextVar('lf_identity', default={})
_validation: ContextVar[dict] = ContextVar('lf_validation', default={})
_PRIVATE = {'authorization', 'password', 'secret_key', 'public_key', 'api_key', 'token',
            'access_token', 'headers', 'image_url', 'inlinedata', 'inline_data', 'image',
            'error', 'exception', 'stacktrace', 'captured_fields', 'memory_states', 'state',
            'latitude', 'longitude', 'location_label', 'lat', 'lng', 'lon'}
_META = {'run_id', 'test_case_id', 'fault_injected', 'correlation_id', 'route', 'provider',
         'attempt', 'outcome', 'session_id', 'environment', 'release', 'usage_status'}


def mask_telemetry(*, data: Any, **kwargs: Any) -> Any:
    from src.agents.guardrails import sanitize_pii

    def clean(value, depth=0):
        if depth > 12:
            return '[REDACTED_DEPTH]'
        if isinstance(value, dict):
            if value.get('type') in {'image_url', 'input_image', 'input_audio'}:
                return {'type': 'text', 'text': '[REDACTED_IMAGE]'}
            if 'messages' in value and ('captured_fields' in value or 'user_role' in value):
                return {k: clean(value[k], depth + 1) for k in ('session_id', 'turn') if k in value}
            return {str(k): '[REDACTED]' if str(k).lower() in _PRIVATE or
                    any(term in str(k).lower() for term in ('api_key', 'secret', 'password'))
                    else clean(v, depth + 1) for k, v in value.items()}
        if isinstance(value, (list, tuple)):
            return [clean(v, depth + 1) for v in value[:100]]
        if isinstance(value, str):
            value = re.sub(r'data:image/[^\s"\']+', '[REDACTED_IMAGE]', value)
            value = re.sub(r'(?i)(?:sk-[\w-]+|pk-lf-[\w-]+|AIza[\w-]+|Bearer\s+\S+)', '[REDACTED_KEY]', value)
            value = re.sub(r'(?i)\b(latitude|longitude|lat|lng|lon)\s*[:=]\s*[-+]?\d*\.?\d+', r'\1=[REDACTED]', value)

            def _mask_vn_coord_pair(m: re.Match) -> str:
                try:
                    c1 = float(m.group(1))
                    c2 = float(m.group(2))
                    if 8.0 <= c1 <= 24.0 and 102.0 <= c2 <= 110.0:
                        return "[COORDINATES_REDACTED]"
                except Exception:
                    pass
                return m.group(0)

            value = re.sub(r'(\b\d{1,2}(?:\.\d+)?)\s*,\s*(\b\d{2,3}(?:\.\d+)?)', _mask_vn_coord_pair, value)
            return sanitize_pii(value[:12000])[0]
        if value is None or isinstance(value, (int, float, bool)):
            return value
        if hasattr(value, 'content'):
            return {'type': getattr(value, 'type', 'message'), 'content': clean(value.content, depth + 1)}
        return '[REDACTED_OBJECT]'

    return clean(data)


def initialize_observability() -> bool:
    global _client
    if os.getenv('LANGFUSE_TRACING_ENABLED', '').lower() == 'false':
        return False
    if _client is not None:
        return True
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parents[2] / '.env', override=False)
    if not os.getenv('LANGFUSE_PUBLIC_KEY') or not os.getenv('LANGFUSE_SECRET_KEY'):
        return False
    try:
        os.environ['LANGFUSE_MEDIA_UPLOAD_ENABLED'] = 'false'
        from langfuse import Langfuse
        _client = Langfuse(public_key=os.environ['LANGFUSE_PUBLIC_KEY'], secret_key=os.environ['LANGFUSE_SECRET_KEY'],
                           base_url=os.getenv('LANGFUSE_BASE_URL', 'https://cloud.langfuse.com'),
                           environment=os.getenv('LANGFUSE_TRACING_ENVIRONMENT', os.getenv('APP_ENV', 'development')),
                           release=os.getenv('LANGFUSE_RELEASE'), mask=mask_telemetry,
                           additional_headers={'x-langfuse-ingestion-version': '4'})
        return True
    except Exception:
        return False


def is_langfuse_available() -> bool:
    return _client is not None


def update_observation(handle: Any, **fields: Any) -> None:
    if handle is not None:
        try:
            if 'metadata' in fields:
                fields['metadata'] = {**_validation.get(), **fields['metadata']}
            handle.update(**{k: mask_telemetry(data=v) if k in {'input', 'output', 'metadata'} else v
                             for k, v in fields.items()})
        except Exception:
            pass


def score_trace(name: str, value: float, *, trace_id: str | None = None,
                data_type: str = 'NUMERIC', comment: str | None = None) -> None:
    """Post a score to the current or given trace. Fail-open — never raises."""
    if _client is None:
        return
    tid = trace_id or getattr(_root.get(), 'trace_id', None)
    if tid is None:
        return
    try:
        _client.score(trace_id=tid, name=name, value=value, data_type=data_type,
                      comment=comment[:500] if comment else None)
    except Exception:
        pass


def current_trace_id() -> str | None:
    return getattr(_root.get(), 'trace_id', None)


def update_trace_identity(*, session_id: str | None, user_id: str | None) -> None:
    identity = dict(_identity.get())
    if session_id:
        identity['session_id'] = session_id
    if user_id:
        identity['user_id'] = sha256(user_id.encode()).hexdigest()
    _identity.set(identity)
    if _root.get() is not None:
        try:
            _root.get().update_trace(**identity)
        except Exception:
            pass


@contextmanager
def validation_context(run_id: str, case_id: str, *, fault_injected: bool = False):
    token = _validation.set({'run_id': run_id, 'test_case_id': case_id,
                             'fault_injected': str(fault_injected).lower()})
    try:
        yield
    finally:
        _validation.reset(token)


@contextmanager
def bind_trace_attributes(*, session_id=None, user_id=None, tags=None, metadata=None):
    identity = dict(_identity.get())
    if session_id:
        identity['session_id'] = session_id
    if user_id:
        identity['user_id'] = sha256(user_id.encode()).hexdigest()
    attrs = {k: str(v) for k, v in {**_validation.get(), **(metadata or {})}.items() if k in _META}
    ctx = nullcontext()
    if _client is not None:
        try:
            from langfuse import propagate_attributes
            ctx = propagate_attributes(**identity, metadata=attrs, tags=tags)
            ctx.__enter__()
        except Exception:
            ctx = nullcontext()
            ctx.__enter__()
    else:
        ctx.__enter__()
    try:
        yield
    finally:
        try:
            ctx.__exit__(None, None, None)
        except Exception:
            pass


@contextmanager
def observation(name: str, *, as_type='span', metadata=None, model=None):
    started = time.monotonic()
    ctx, handle = None, None
    parent = _root.get()
    identity_token = _identity.set(dict(_identity.get()))
    merged = {**_validation.get(), **_identity.get(), **(metadata or {})}
    merged.pop('user_id', None)
    if _client is not None:
        try:
            # The SDK creates a trace for a parentless observation. A second
            # synthetic observation duplicates roots and separates usage/errors
            # from the generation the caller owns.
            ctx = _client.start_as_current_observation(name=name, as_type=as_type,
                                                       metadata=mask_telemetry(data=merged), model=model)
            handle = ctx.__enter__()
        except Exception:
            ctx = None
    root_token = _root.set(handle if parent is None else parent)
    try:
        with bind_trace_attributes():
            yield handle
    except BaseException as exc:
        from src.services.agent_llm import classify_provider_error
        from src.services.request_diagnostics import failure_details
        outcome = 'cancelled' if isinstance(exc, asyncio.CancelledError) else classify_provider_error(exc)
        update_observation(handle, level='ERROR', status_message=outcome,
                           metadata={**merged, 'outcome': outcome, 'failure_stage': name,
                                     'elapsed_ms': round((time.monotonic() - started) * 1000, 3),
                                     **failure_details(exc)})
        raise
    finally:
        _root.reset(root_token)
        _identity.reset(identity_token)
        if ctx is not None:
            try:
                ctx.__exit__(None, None, None)
            except Exception:
                pass


def get_tracer_callbacks(session_id=None, user_id=None, tags=None, metadata=None) -> list[Any]:
    if _client is None:
        return []
    try:
        from langfuse.langchain import CallbackHandler
        from src.services.langfuse_callback import safe_callback
        return [safe_callback(CallbackHandler)(public_key=os.getenv('LANGFUSE_PUBLIC_KEY'), update_trace=False)]
    except Exception:
        return []


def trace_endpoint(name: str):
    def decorate(function):
        @functools.wraps(function)
        async def wrapped(*args, **kwargs):
            with observation(name, metadata={'route': name, 'layer': 'api'}) as root:
                arguments = inspect.signature(function).bind_partial(*args, **kwargs).arguments
                payload = arguments.get('payload')
                user = arguments.get('current_user')
                if payload is not None:
                    request_id = getattr(payload, 'request_id', None)
                    if request_id:
                        update_observation(root, metadata={'route': name, 'layer': 'api', 'request_id': str(request_id)[:128]})
                    update_trace_identity(session_id=getattr(payload, 'session_id', None),
                                          user_id=getattr(user, 'id', None))
                result = await function(*args, **kwargs)
                data = getattr(result, 'data', result)
                personal = getattr(data, '_personal_memory_diagnostics', None)
                output = ({'personal_memory': personal} if personal is not None else
                          data.model_dump() if hasattr(data, 'model_dump') else data)
                update_observation(root, output=output,
                                   metadata={**_validation.get(), 'route': name, 'outcome': 'completed'})
                return result
        return wrapped
    return decorate


async def flush_observability(*, shutdown: bool = False) -> None:
    global _client
    client = _client
    if client is None:
        return
    try:
        await asyncio.to_thread(client.flush)
    except Exception:
        pass
    finally:
        if shutdown:
            try:
                await asyncio.to_thread(client.shutdown)
            except Exception:
                pass
            _client = None
