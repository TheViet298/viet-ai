import pytest
from unittest.mock import AsyncMock, MagicMock
from src.config import get_settings
from src.services.vehicle_vision_service import recognize_vehicle_model


@pytest.mark.asyncio
async def test_recognize_vehicle_model_success(monkeypatch):
    import src.services.vehicle_vision_service as v_mod

    settings = get_settings()
    monkeypatch.setattr(settings, "agent_llm_enabled", True)
    monkeypatch.setattr(settings, "openai_api_key", "mock-openai-key")
    monkeypatch.setattr(settings, "vision_model", "gpt-6-luna")

    mock_client = MagicMock()
    mock_chat = MagicMock()
    mock_completions = MagicMock()

    mock_response = MagicMock()
    mock_choice = MagicMock()
    mock_choice.finish_reason = "stop"
    mock_choice.message.content = '{"is_vinfast": true, "vehicle_model": "VF 3", "confidence": 0.95, "candidates": [{"label": "VF 3", "confidence": 0.95}]}'
    mock_response.choices = [mock_choice]

    mock_completions.create = AsyncMock(return_value=mock_response)
    mock_chat.completions = mock_completions
    mock_client.chat = mock_chat

    monkeypatch.setattr(v_mod, "get_async_openai_client", lambda: mock_client)

    result = await recognize_vehicle_model(b"fake_vf3_image", "image/jpeg")
    assert result["status"] == "candidate"
    assert result["model_label"] == "VF 3"
    assert result["candidates"][0]["confidence"] == 0.95
    assert result["requires_user_confirmation"] is True


@pytest.mark.asyncio
async def test_recognize_vehicle_model_unknown_when_not_vinfast(monkeypatch):
    import src.services.vehicle_vision_service as v_mod

    settings = get_settings()
    monkeypatch.setattr(settings, "agent_llm_enabled", True)
    monkeypatch.setattr(settings, "openai_api_key", "mock-openai-key")
    monkeypatch.setattr(settings, "vision_model", "gpt-6-luna")

    mock_client = MagicMock()
    mock_chat = MagicMock()
    mock_completions = MagicMock()

    mock_response = MagicMock()
    mock_choice = MagicMock()
    mock_choice.finish_reason = "stop"
    mock_choice.message.content = '{"is_vinfast": false, "vehicle_model": "unknown", "confidence": 0.2, "candidates": [{"label": "unknown", "confidence": 0.2}]}'
    mock_response.choices = [mock_choice]

    mock_completions.create = AsyncMock(return_value=mock_response)
    mock_chat.completions = mock_completions
    mock_client.chat = mock_chat

    monkeypatch.setattr(v_mod, "get_async_openai_client", lambda: mock_client)

    result = await recognize_vehicle_model(b"fake_non_vinfast_image", "image/jpeg")
    assert result["status"] == "unknown"
    assert result["model_label"] is None


@pytest.mark.asyncio
async def test_recognize_vehicle_model_timeout_handled(monkeypatch):
    import src.services.vehicle_vision_service as v_mod

    settings = get_settings()
    monkeypatch.setattr(settings, "agent_llm_enabled", True)
    monkeypatch.setattr(settings, "openai_api_key", "mock-openai-key")

    mock_client = MagicMock()
    mock_chat = MagicMock()
    mock_completions = MagicMock()
    mock_completions.create = AsyncMock(side_effect=TimeoutError("Request timed out"))
    mock_chat.completions = mock_completions
    mock_client.chat = mock_chat

    monkeypatch.setattr(v_mod, "get_async_openai_client", lambda: mock_client)

    result = await recognize_vehicle_model(b"fake_image", "image/jpeg")
    assert result["status"] == "unavailable"
    assert result["reason"] == "inference_timeout"

