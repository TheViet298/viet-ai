import pytest
from unittest.mock import patch
from pydantic import BaseModel
from src.agents.state import AgentState
from src.services.agent_llm import structured_call, classify_provider_error, record_outcome

class DummySchema(BaseModel):
    answer: str

def test_classify_provider_error_variants():
    assert classify_provider_error(Exception("429 Too Many Requests")) == "rate_limited"
    assert classify_provider_error(Exception("401 Unauthorized API key")) == "auth_error"
    assert classify_provider_error(Exception("Server connection reset")) == "provider_error"
    assert classify_provider_error(TimeoutError("Operation timed out")) == "timeout"

def test_record_outcome_stores_last_llm_outcome():
    state: AgentState = {"session_id": "test_sess", "turn": 1}
    record_outcome(state, "test_prompt", "circuit_open")
    assert state.get("last_llm_outcome") == "circuit_open"

@pytest.mark.asyncio
async def test_structured_call_records_context_budget_exceeded():
    state: AgentState = {"session_id": "test_sess", "turn": 1}
    with patch("src.services.agent_llm.get_settings") as mock_settings:
        mock_settings.return_value.google_api_key = "fake_key"
        mock_settings.return_value.agent_llm_enabled = True
        mock_settings.return_value.agent_turn_timeout_s = 10
        mock_settings.return_value.agent_context_max_bytes = 10  # Very small budget to trigger error
        with patch("src.services.agent_llm.load_prompt", return_value="test prompt"):
            res = await structured_call(state, "test_prompt", DummySchema)
            assert res is None
            assert state.get("last_llm_outcome") == "context_budget_exceeded"
