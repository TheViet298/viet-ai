import pytest

from src.services.location_privacy import LocationQueryPrivacyMiddleware


@pytest.mark.asyncio
@pytest.mark.parametrize('status', [200, 307, 422, 503])
@pytest.mark.parametrize('suffix', ['', '/'])
async def test_nearby_query_available_to_handler_but_removed_before_access_log(status, suffix):
    scope = {'type': 'http', 'path': '/api/v1/customer/service-points/nearby' + suffix,
             'query_string': b'lat=21.0315&lng=105.8145'}
    seen = []

    async def handler(scope, receive, send):
        seen.append(scope['query_string'])
        await send({'type': 'http.response.start', 'status': status, 'headers': []})
        await send({'type': 'http.response.body', 'body': b'{}'})

    async def send(message):
        if message['type'] == 'http.response.start':
            seen.append(scope['query_string'])

    await LocationQueryPrivacyMiddleware(handler)(scope, None, send)
    assert seen == [b'lat=21.0315&lng=105.8145', b'']
