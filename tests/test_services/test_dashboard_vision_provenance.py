"""Provider provenance must describe the selected vision transport on every path."""

import json
from types import SimpleNamespace

import httpx
import pytest
from openai import AsyncOpenAI

from src.services import dashboard_vision_service as vision


OBSERVATION = {
    "is_dashboard": True,
    "ocr_text": "Tire pressure low",
    "symptom_keys": ["low_pressure"],
    "confidence": 0.95,
    "wheel_position": "rear_right",
    "observations": [],
}


@pytest.fixture
def settings(monkeypatch):
    configured = SimpleNamespace(
        agent_llm_enabled=True, dashboard_vision_enabled=True,
        vision_provider="openai", openai_api_key="test-openai-key",
        google_api_key="test-google-key", vision_model="requested-openai-model",
        dashboard_vision_model="requested-google-model", dashboard_vision_timeout_s=1,
    )
    monkeypatch.setattr(vision, "get_settings", lambda: configured)
    return configured


@pytest.mark.asyncio
@pytest.mark.parametrize("provider,evidence,model", [
    ("openai", "OPENAI_VISION", "requested-openai-model"),
    ("google", "GEMINI_VISION", "requested-google-model"),
])
@pytest.mark.parametrize("outcome,error", [
    ("success", None), ("authentication", "vision_authentication_failed"),
    ("timeout", "vision_timeout"), ("malformed", "vision_request_failed"),
    ("request_failed", "vision_request_failed"),
])
async def test_selected_provider_provenance_survives_success_and_errors(
    monkeypatch, settings, provider, evidence, model, outcome, error,
):
    settings.vision_provider = provider
    requests = []

    def handle(request):
        requests.append(request)
        if outcome == "timeout":
            raise httpx.ReadTimeout("private transport detail", request=request)
        if outcome in {"authentication", "request_failed"}:
            return httpx.Response(401 if outcome == "authentication" else 500,
                                  json={"error": {"message": "private transport detail"}})
        content = "not-json" if outcome == "malformed" else json.dumps(OBSERVATION)
        if provider == "openai":
            assert json.loads(request.content)["model"] == model
            return httpx.Response(200, json={
                "id": "test", "object": "chat.completion", "created": 1, "model": model,
                "choices": [{"index": 0, "finish_reason": "stop",
                             "message": {"role": "assistant", "content": content}}],
            })
        assert model in str(request.url)
        return httpx.Response(200, json={"candidates": [{
            "finishReason": "STOP", "content": {"parts": [{"text": content}]},
        }]})

    transport = httpx.AsyncClient(transport=httpx.MockTransport(handle))
    try:
        if provider == "openai":
            sdk = AsyncOpenAI(api_key="test-openai-key", http_client=transport, max_retries=0)
            monkeypatch.setattr(vision, "get_async_openai_client", lambda: sdk)
        else:
            monkeypatch.setattr(vision, "AsyncClient", lambda **kwargs: transport)
        result = await vision.analyze_dashboard_image(b"validated-image", "image/png")
    finally:
        await transport.aclose()

    assert len(requests) == 1
    assert result["evidence_type"] == evidence
    assert result["model_version"] == model
    assert result.get("analysis_error") == error
    if outcome == "success":
        assert result["symptom_keys"] == ["low_pressure"]
        assert result["confidence"] == 0.95
    assert "private transport detail" not in json.dumps(result)


@pytest.mark.asyncio
@pytest.mark.parametrize("provider,evidence,model", [
    ("openai", "OPENAI_VISION", "requested-openai-model"),
    ("google", "GEMINI_VISION", "requested-google-model"),
])
@pytest.mark.parametrize("unavailable", ["missing_key", "agent_disabled", "dashboard_disabled"])
async def test_unavailable_configuration_keeps_selected_provenance_without_fallback(
    monkeypatch, settings, provider, evidence, model, unavailable,
):
    settings.vision_provider = provider
    if unavailable == "missing_key":
        setattr(settings, "openai_api_key" if provider == "openai" else "google_api_key", "")
    else:
        setattr(settings, "agent_llm_enabled" if unavailable == "agent_disabled" else "dashboard_vision_enabled", False)

    def unexpected(*args, **kwargs):
        pytest.fail("Unavailable selected provider must not call or fall back to another provider")

    monkeypatch.setattr(vision, "get_async_openai_client", unexpected)
    monkeypatch.setattr(vision, "AsyncClient", unexpected)
    result = await vision.analyze_dashboard_image(b"validated-image", "image/png")
    assert result["analysis_error"] == "vision_unavailable"
    assert result["evidence_type"] == evidence
    assert result["model_version"] == model

