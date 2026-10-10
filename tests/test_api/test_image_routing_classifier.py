import json

import httpx
import pytest

from src.config import get_settings
from src.services.image_routing import classify_vehicle_image


@pytest.mark.asyncio
@pytest.mark.parametrize("body,finish,status,expected", [
    ({"image_kind": "exterior", "confidence": .95}, "STOP", 200, "exterior"),
    ({"image_kind": "dashboard", "confidence": .9}, "STOP", 200, "dashboard"),
    ({"image_kind": "charger", "confidence": .95}, "STOP", 200, "charger"),
    ({"image_kind": "exterior", "confidence": .4}, "STOP", 200, "unknown"),
    ({"image_kind": "unknown", "confidence": .99}, "STOP", 200, "unknown"),
    ({"image_kind": "exterior", "confidence": .99}, "MAX_TOKENS", 200, "unknown"),
    ({"image_kind": "exterior", "confidence": .99}, "STOP", 503, "unknown"),
    ({"image_kind": "dashboard", "confidence": .99, "diagnosis": "confirmed"}, "STOP", 200, "unknown"),
])
async def test_classifier_schema_confidence_and_provider_failures(monkeypatch, body, finish, status, expected):
    import src.services.image_routing as module
    settings = get_settings()
    monkeypatch.setattr(settings, "agent_llm_enabled", True)
    monkeypatch.setattr(settings, "vision_provider", "google")
    monkeypatch.setattr(settings, "google_api_key", "routing-test-key")
    requests = []
    def handler(request):
        requests.append(json.loads(request.content))
        return httpx.Response(status, json={"candidates": [{"finishReason": finish,
                             "content": {"parts": [{"text": json.dumps(body)}]}}]})
    monkeypatch.setattr(module, "AsyncClient", lambda **kwargs: httpx.AsyncClient(transport=httpx.MockTransport(handler), **kwargs))
    result = await classify_vehicle_image(b"clean-image-bytes", "image/png")
    assert result["image_kind"] == expected
    assert requests[0]["contents"][0]["parts"][1]["inlineData"]["mimeType"] == "image/png"
    assert "fileName" not in requests[0]["contents"][0]["parts"][1]["inlineData"]
    assert "routing-test-key" not in json.dumps(result)


@pytest.mark.asyncio
async def test_classify_vehicle_image_openai_provider(monkeypatch):
    import src.services.image_routing as routing_mod
    from unittest.mock import AsyncMock, MagicMock

    settings = get_settings()
    monkeypatch.setattr(settings, "agent_llm_enabled", True)
    monkeypatch.setattr(settings, "vision_provider", "openai")
    monkeypatch.setattr(settings, "openai_api_key", "mock-openai-key")
    monkeypatch.setattr(settings, "vision_model", "gpt-6-luna")

    mock_client = MagicMock()
    mock_chat = MagicMock()
    mock_completions = MagicMock()

    mock_response = MagicMock()
    mock_choice = MagicMock()
    mock_choice.finish_reason = "stop"
    mock_choice.message.content = '{"image_kind": "exterior", "confidence": 0.95}'
    mock_response.choices = [mock_choice]

    mock_completions.create = AsyncMock(return_value=mock_response)
    mock_chat.completions = mock_completions
    mock_client.chat = mock_chat

    monkeypatch.setattr(routing_mod, "get_async_openai_client", lambda: mock_client)

    result = await classify_vehicle_image(b"fake_image_bytes", "image/png")
    assert result["image_kind"] == "exterior"
    assert result["confidence"] >= 0.8

