import asyncio
import time

import pytest

from src.agents.nodes.rag_node import rag_node


@pytest.mark.asyncio
async def test_slow_retrieval_respects_remaining_turn_budget(monkeypatch):
    async def slow(*args, **kwargs):
        await asyncio.sleep(0.2)
        return {"status": "NO_SOURCE", "citations": []}

    monkeypatch.setattr("src.agents.nodes.rag_node.vinfast_manual_search", slow)
    start = time.monotonic()
    result = await rag_node({"latest_user_message": "Bảo hành VF8?", "confidence_score": 0.9,
                             "llm_budget": {"deadline": start + 0.02, "attempts": 0}})
    assert time.monotonic() - start < 0.15
    assert result["is_no_source"]
    assert result["retrieval_diagnostics"]["status"] == "timeout"


@pytest.mark.asyncio
async def test_nonpublic_battery_information_does_not_ask_for_incident_fields():
    from src.agents.graph import agent

    result = await agent.ainvoke({"query": "Tài liệu không công khai về pin VF8", "user_role": "customer"})
    assert result["is_no_source"]
    assert result["response_type"] != "CLARIFICATION"
