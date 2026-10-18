import pytest
from src.services import agent_llm


def test_interpretation_reserves_generation_and_total_cap(monkeypatch):
    monkeypatch.setattr(agent_llm.time, 'monotonic', lambda: 10)
    budget = agent_llm.new_turn_budget(30)
    assert agent_llm.claim_model_attempt(budget, 'interpretation')
    assert agent_llm.claim_model_attempt(budget, 'interpretation')
    assert not agent_llm.claim_model_attempt(budget, 'interpretation')
    assert agent_llm.claim_model_attempt(budget, 'generation')
    assert not agent_llm.claim_model_attempt(budget, 'generation')
    assert agent_llm.claim_model_attempt(budget, 'normalization')
    assert not agent_llm.claim_model_attempt(budget, 'normalization')
    assert budget['attempts'] == 3
    budget['deadline'] = 9
    assert not agent_llm.claim_model_attempt(budget, 'generation')


@pytest.mark.asyncio
async def test_concurrent_claims_share_one_budget(monkeypatch):
    import asyncio
    monkeypatch.setattr(agent_llm.time, 'monotonic', lambda: 10)
    budget = agent_llm.new_turn_budget(30)
    async def claim():
        return agent_llm.claim_model_attempt(budget, 'generation')
    assert sum(await asyncio.gather(*(claim() for _ in range(10)))) == 2
