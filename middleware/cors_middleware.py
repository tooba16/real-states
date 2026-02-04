from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from starlette.requests import Request
from starlette.types import ASGIApp
from fastapi import FastAPI
import time

class CORSMiddleware:
    def __init__(
        self,
        app: ASGIApp,
        allow_origins: list = None,
        allow_credentials: bool = True,
        allow_methods: list = None,
        allow_headers: list = None,
    ):
        self.app = app
        self.allow_origins = allow_origins or ["*"]
        self.allow_credentials = allow_credentials
        self.allow_methods = allow_methods or ["*"]
        self.allow_headers = allow_headers or ["*"]

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Handle CORS preflight
        if scope["method"] == "OPTIONS":
            headers = {
                "access-control-allow-origin": "*",
                "access-control-allow-credentials": str(self.allow_credentials).lower(),
                "access-control-allow-methods": ", ".join(self.allow_methods),
                "access-control-allow-headers": ", ".join(self.allow_headers),
                "access-control-max-age": "86400",
            }

            async def send_wrapper(message):
                if message["type"] == "http.response.start":
                    message["headers"] = [
                        (k.encode(), v.encode()) for k, v in headers.items()
                    ] + message.get("headers", [])
                await send(message)

            await self.app(scope, receive, send_wrapper)
            return

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                headers = [
                    (k, v) for k, v in message.get("headers", [])
                    if k.lower() not in [b"access-control-allow-origin"]
                ]

                headers.append((b"access-control-allow-origin", b"*"))
                headers.append((b"access-control-allow-credentials", b"true"))
                headers.append((b"access-control-allow-methods", b", ".join([m.encode() for m in self.allow_methods])))
                headers.append((b"access-control-allow-headers", b", ".join([h.encode() for h in self.allow_headers])))

                message["headers"] = headers

            await send(message)

        await self.app(scope, receive, send_wrapper)