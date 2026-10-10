import json

import httpx
import pytest
from openai import AsyncOpenAI

from src.config import get_settings


@pytest.mark.asyncio
@pytest.mark.parametrize('stage', ['routing', 'vehicle', 'dashboard'])
async def test_vision_request_uses_supported_model_parameters(monkeypatch, stage):
    from src.services import dashboard_vision_service, image_routing, vehicle_vision_service

    settings = get_settings()
    for name, value in [('agent_llm_enabled', True), ('dashboard_vision_enabled', True),
                        ('vision_provider', 'openai'), ('openai_api_key', 'transport-test'),
                        ('vision_model', 'gpt-6-luna')]:
        monkeypatch.setattr(settings, name, value)
    bodies = {
        'routing': {'image_kind': 'exterior', 'confidence': .95},
        'vehicle': {'is_vinfast': True, 'vehicle_model': 'VF 6', 'confidence': .95, 'candidates': []},
        'dashboard': {'is_dashboard': True, 'ocr_text': 'Tire pressure low',
                      'symptom_keys': ['low_pressure'], 'confidence': .95,
                      'wheel_position': 'rear_right', 'observations': []},
    }

    def handler(request):
        payload = json.loads(request.content)
        if 'max_tokens' in payload or payload.get('temperature') == 0:
            return httpx.Response(400, json={'error': {'message': 'Unsupported parameter',
                                  'type': 'invalid_request_error', 'code': 'unsupported_parameter'}})
        assert payload['max_completion_tokens'] > 0
        if stage == 'routing':
            assert payload.get('reasoning_effort') == 'none'
        if stage == 'dashboard' and 'JSON' not in payload['messages'][0]['content'][0]['text']:
            return httpx.Response(400, json={'error': {'message': 'JSON mode requires JSON instructions',
                                  'type': 'invalid_request_error'}})
        assert payload['messages'][0]['content'][1]['image_url']['url'].startswith('data:image/png;base64,')
        return httpx.Response(200, json={'id': 'chatcmpl-test', 'object': 'chat.completion',
            'created': 1, 'model': 'gpt-6-luna', 'choices': [{'index': 0, 'finish_reason': 'stop',
            'message': {'role': 'assistant', 'content': json.dumps(bodies[stage])}}]})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as transport:
        sdk = AsyncOpenAI(api_key='transport-test', http_client=transport, max_retries=0)
        module = {'routing': image_routing, 'vehicle': vehicle_vision_service,
                  'dashboard': dashboard_vision_service}[stage]
        monkeypatch.setattr(module, 'get_async_openai_client', lambda: sdk)
        operation = {'routing': image_routing.classify_vehicle_image,
                     'vehicle': vehicle_vision_service.recognize_vehicle_model,
                     'dashboard': dashboard_vision_service.analyze_dashboard_image}[stage]
        result = await operation(b'clean-test-image', 'image/png')
    if stage == 'routing':
        assert result['image_kind'] == 'exterior'
    elif stage == 'vehicle':
        assert result['status'] == 'candidate'
        assert result['model_label'] == 'VF 6'
    else:
        assert result['symptom_keys'] == ['low_pressure']
        assert 'analysis_error' not in result


pytest_plugins = ['tests.test_api.test_customer_chat_regressions']


@pytest.mark.asyncio
async def test_routing_keeps_safe_provider_error_category(monkeypatch):
    from src.services import image_routing

    settings = get_settings()
    monkeypatch.setattr(settings, 'agent_llm_enabled', True)
    monkeypatch.setattr(settings, 'vision_provider', 'openai')
    monkeypatch.setattr(settings, 'openai_api_key', 'private-test-key')
    def handler(request):
        return httpx.Response(400, json={'error': {'message': 'private-test-key',
            'type': 'invalid_request_error', 'code': 'unsupported_parameter', 'param': 'max_tokens'}})
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as transport:
        sdk = AsyncOpenAI(api_key='private-test-key', http_client=transport, max_retries=0)
        monkeypatch.setattr(image_routing, 'get_async_openai_client', lambda: sdk)
        result = await image_routing.classify_vehicle_image(b'image', 'image/png')
    assert result['reason'] == 'routing_request_failed'
    assert result['provider_code'] == 'unsupported_parameter'
    assert result['provider_parameter'] == 'max_tokens'
    assert 'private-test-key' not in json.dumps(result)


@pytest.mark.asyncio
async def test_upload_preserves_service_failure_instead_of_blaming_image(client, customer_db, monkeypatch):
    import io

    from PIL import Image

    import src.api.customer as api

    async def unavailable(*args):
        return {'image_kind': 'unknown', 'confidence': 0, 'reason': 'routing_unavailable'}
    monkeypatch.setattr(api, 'classify_vehicle_image', unavailable)
    buffer = io.BytesIO()
    Image.new('RGB', (16, 16)).save(buffer, format='PNG')
    response = await client.post('/api/v1/customer/attachments', data={'image_kind': 'auto'},
        files={'file': ('photo.png', buffer.getvalue(), 'image/png')})
    data = response.json()['data']
    assert data['analysis_status'] == 'FAILED'
    assert data['detected_signals']['analysis_error'] == 'routing_unavailable'
