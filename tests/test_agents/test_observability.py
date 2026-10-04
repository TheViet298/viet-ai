from src.services.observability import get_tracer_callbacks, is_langfuse_available


def test_cloud_trace_is_optional(monkeypatch):
    monkeypatch.delenv("LANGFUSE_PUBLIC_KEY", raising=False)
    monkeypatch.delenv("LANGFUSE_SECRET_KEY", raising=False)
    assert not is_langfuse_available()
    assert get_tracer_callbacks() == []
