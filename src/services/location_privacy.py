"""Keep nearby coordinates out of the application's ASGI access-log scope."""
from starlette.types import ASGIApp, Message, Receive, Scope, Send


class LocationQueryPrivacyMiddleware:
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope['type'] != 'http' or scope.get('path', '').rstrip('/') != '/api/v1/customer/service-points/nearby':
            await self.app(scope, receive, send)
            return

        # Routing and validation see the original parameters. Uvicorn writes its
        # access line upon response.start; remove the query before that point.
        async def private_send(message: Message):
            if message['type'] == 'http.response.start':
                scope['query_string'] = b''
            await send(message)

        await self.app(scope, receive, private_send)
