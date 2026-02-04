from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp
from utils.logger import logger
import time
import json
from urllib.parse import urlparse

class LoggingMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next):
        start_time = time.time()

        # Log incoming request
        logger.info(
            f"REQUEST: {request.method} {request.url.path} "
            f"FROM: {request.client.host}:{request.client.port} "
            f"USER_AGENT: {request.headers.get('user-agent', 'Unknown')}"
        )

        try:
            response = await call_next(request)
        except Exception as e:
            # Log error
            logger.error(f"ERROR in {request.method} {request.url.path}: {str(e)}")
            raise e
        finally:
            # Calculate duration
            duration = time.time() - start_time

            # Log response
            logger.info(
                f"RESPONSE: {response.status_code} for {request.method} {request.url.path} "
                f"DURATION: {duration:.3f}s"
            )

        return response