import asyncio

import pytest

from src.agents.nodes.triage_node import TriageResult
from src.config import get_settings
from src.services.agent_llm import structured_call
from src.services.tracer import replay_session


@pytest.fixture
def enabled_llm(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "agent_llm_enabled", True)
    monkeypatch.setattr(settings, "google_api_key", "budget-test-secret")
    from src.services import agent_llm
    if hasattr(agent_llm, "reset_circuits"):
        agent_llm.reset_circuits()


@pytest.mark.asyncio
async def test_rate_limit_opens_circuit_without_leaking_exception(enabled_llm, monkeypatch):
    from src.services import llm
    calls = []

    class Fake:
        def with_structured_output(self, *args, **kwargs):
            return self

        async def ainvoke(self, messages):
            calls.append(1)
            raise RuntimeError("429 quota budget-test-secret")

    monkeypatch.setattr(llm, "get_llm", Fake)
    for turn in [1, 2]:
        assert await structured_call({"query": "VF8", "session_id": "quota", "turn": turn}, "triage", TriageResult) is None
    assert len(calls) == 1
    events = replay_session("quota")
    assert {e["gate_decision"] for e in events} == {"rate_limited", "circuit_open"}
    assert "budget-test-secret" not in str(events)


@pytest.mark.asyncio
async def test_turn_budget_prevents_second_foreground_call(enabled_llm, monkeypatch):
    from src.services import llm
    calls = []
    parsed = TriageResult(intent="Sales/General Info", priority="LOW", confidence_score=0.9)

    class Fake:
        def with_structured_output(self, *args, **kwargs):
            return self

        async def ainvoke(self, messages):
            calls.append(1)
            return {"parsed": parsed, "raw": None}

    monkeypatch.setattr(llm, "get_llm", Fake)
    state = {"query": "VF8", "session_id": "one-call"}
    assert await structured_call(state, "triage", TriageResult) == parsed
    assert await structured_call(state, "triage", TriageResult) is None
    assert len(calls) == 1


@pytest.mark.asyncio
async def test_timeout_has_observable_reason(enabled_llm, monkeypatch):
    from src.services import llm
    monkeypatch.setattr(get_settings(), "agent_llm_timeout_s", 0.02, raising=False)

    class Fake:
        def with_structured_output(self, *args, **kwargs):
            return self

        async def ainvoke(self, messages):
            await asyncio.sleep(1)

    monkeypatch.setattr(llm, "get_llm", Fake)
    assert await structured_call({"query": "VF8", "session_id": "slow-model"}, "triage", TriageResult) is None
    assert replay_session("slow-model")[-1]["gate_decision"] == "timeout"


@pytest.mark.asyncio
async def test_old_success_cannot_close_new_quota_circuit(enabled_llm, monkeypatch):
    from src.services import agent_llm, llm
    started, release = asyncio.Event(), asyncio.Event()
    calls = []
    parsed = TriageResult(intent="Sales/General Info", priority="LOW", confidence_score=0.9)

    class Fake:
        def with_structured_output(self, *args, **kwargs):
            return self

        async def ainvoke(self, messages):
            calls.append(1)
            if len(calls) == 1:
                started.set()
                await release.wait()
                return {"parsed": parsed}
            raise RuntimeError("429 quota")

    monkeypatch.setattr(llm, "get_llm", Fake)
    old = asyncio.create_task(structured_call({"session_id": "old"}, "triage", TriageResult))
    await started.wait()
    await structured_call({"session_id": "new"}, "triage", TriageResult)
    release.set()
    await old
    assert agent_llm.circuit_key() in agent_llm._circuits
    await structured_call({"session_id": "blocked"}, "triage", TriageResult)
    assert len(calls) == 2


@pytest.mark.asyncio
async def test_cancelled_probe_can_recover(enabled_llm, monkeypatch):
    import time

    from src.services import agent_llm, llm
    started = asyncio.Event()

    class Fake:
        def with_structured_output(self, *args, **kwargs):
            return self

        async def ainvoke(self, messages):
            started.set()
            await asyncio.Event().wait()

    monkeypatch.setattr(llm, "get_llm", Fake)
    agent_llm.open_circuit()
    key = agent_llm.circuit_key()
    agent_llm._circuits[key]["until"] = time.monotonic() - 1
    probe = asyncio.create_task(structured_call({"session_id": "cancelled-probe"}, "triage", TriageResult))
    await started.wait()
    probe.cancel()
    with pytest.raises(asyncio.CancelledError):
        await probe
    assert agent_llm._circuits[key]["probe"] is False
    assert replay_session("cancelled-probe")[-1]["gate_decision"] == "cancelled"
