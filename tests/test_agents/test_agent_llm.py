from types import SimpleNamespace

import pytest

from src.agents.nodes.triage_node import TriageResult
from src.config import get_settings
from src.services.agent_llm import structured_call
from src.services.tracer import replay_session


@pytest.mark.asyncio
async def test_structured_generation_records_usage_not_internal_reasoning(monkeypatch):
    from src.services import llm

    settings = get_settings()
    monkeypatch.setattr(settings, "agent_llm_enabled", True)
    monkeypatch.setattr(settings, "google_api_key", "fake-test-key")
    parsed = TriageResult(intent="Sales/General Info", priority="LOW", confidence_score=0.9, is_faq=True)

    class FakeModel:
        def with_structured_output(self, schema, include_raw):
            assert schema is TriageResult and include_raw
            return self

        async def ainvoke(self, messages):
            assert "chính sách" in str(messages).lower()
            return {
                "parsed": parsed,
                "raw": SimpleNamespace(
                    content="private reasoning", usage_metadata={"input_tokens": 200, "output_tokens": 30}
                ),
            }

    monkeypatch.setattr(llm, "get_llm", FakeModel)
    result = await structured_call({"query": "Chính sách VF8?", "session_id": "llm-test"}, "triage", TriageResult)
    assert result == parsed
    event = replay_session("llm-test")[0]
    assert event["tokens_in"] == 200 and event["tokens_out"] == 30
    assert "private reasoning" not in str(event)


@pytest.mark.asyncio
async def test_provider_failure_returns_safe_fallback(monkeypatch):
    from src.services import llm

    settings = get_settings()
    monkeypatch.setattr(settings, "agent_llm_enabled", True)
    monkeypatch.setattr(settings, "google_api_key", "fake-test-key")

    def unavailable():
        raise RuntimeError("Provider unavailable")

    monkeypatch.setattr(llm, "get_llm", unavailable)
    assert await structured_call({"query": "VF8"}, "triage", TriageResult) is None
