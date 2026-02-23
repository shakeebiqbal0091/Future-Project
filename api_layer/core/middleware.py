import logging
from fastapi import FastAPI, Request, Response
from fastapi.middleware.base import BaseHTTPMiddleware
from fastapi.responses import JSONResponse
import time
from typing import Any, Dict, Optional

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging requests and responses."""

    def __init__(self, app: FastAPI, logger: logging.Logger = None):
        super().__init__(app)
        self.logger = logger or logging.getLogger(__name__)

    async def dispatch(self, request: Request, call_next):
        start_time = time.time()

        # Log request
        request_data = {
            "method": request.method,
            "url": str(request.url),
            "headers": dict(request.headers),
            "client": request.client.host if request.client else "unknown"
        }

        if request.method in ["POST", "PUT", "PATCH"]:
            try:
                body = await request.json()
                request_data["body"] = body
            except:
                request_data["body"] = "unable to parse"

        self.logger.info(f"Request: {request_data}")

        # Process request
        response = await call_next(request)

        # Calculate processing time
        processing_time = time.time() - start_time

        # Log response
        response_data = {
            "status_code": response.status_code,
            "processing_time": f"{processing_time:.3f}s"
        }

        if hasattr(response, "json"):
            try:
                response_data["body"] = await response.json()
            except:
                response_data["body"] = "unable to parse"

        self.logger.info(f"Response: {response_data}")

        return response

class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """Middleware for handling errors and exceptions."""

    def __init__(self, app: FastAPI, logger: logging.Logger = None):
        super().__init__(app)
        self.logger = logger or logging.getLogger(__name__)

    async def dispatch(self, request: Request, call_next):
        try:
            response = await call_next(request)
            return response
        except Exception as e:
            self.logger.error(f"Unhandled exception: {str(e)}", exc_info=True)

            return JSONResponse(
                status_code=500,
                content={"detail": "Internal server error", "error": str(e)}
            )

class RateLimitingMiddleware(BaseHTTPMiddleware):
    """Middleware for rate limiting."""

    def __init__(self, app: FastAPI, rate_limit: int = 100, window: int = 60):
        super().__init__(app)
        self.rate_limit = rate_limit
        self.window = window
        self.requests: Dict[str, List[float]] = {}

    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host if request.client else "unknown"
        current_time = time.time()

        # Clean up old requests
        if client_ip in self.requests:
            self.requests[client_ip] = [
                t for t in self.requests[client_ip]
                if current_time - t < self.window
            ]
        else:
            self.requests[client_ip] = []

        # Check rate limit
        if len(self.requests[client_ip]) >= self.rate_limit:
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded"}
            )

        # Record request
        self.requests[client_ip].append(current_time)

        response = await call_next(request)
        return response

class CORSMiddlewareWrapper:
    """Wrapper for CORS middleware with additional logging."""

    def __init__(self, app: FastAPI, allow_origins: List[str]):
        self.app = app
        self.allow_origins = allow_origins

    def __call__(self, scope):
        if scope["type"] != "http":
            return self.app(scope)

        # Add CORS headers
        async def middleware_handler(scope, receive, send):
            async def wrapped_send(message):
                if message["type"] == "http.response.start":
                    message["headers"] = [
                        *message["headers"],
                        (b"access-control-allow-origin", b"".join(self.allow_origins).encode()),
                        (b"access-control-allow-credentials", b"true"),
                        (b"access-control-allow-methods", b"GET, POST, PUT, DELETE, OPTIONS"),
                        (b"access-control-allow-headers", b"Content-Type, Authorization, X-Requested-With"),
                    ]
                await send(message)

            if scope["method"] == "OPTIONS":
                # Handle preflight requests
                async def send_preflight():
                    await wrapped_send({
                        "type": "http.response.start",
                        "status": 200,
                        "headers": [],
                    })
                    await wrapped_send({
                        "type": "http.response.body",
                        "body": b"",
                    })

                return await send_preflight()

            return await self.app(scope, receive, wrapped_send)

        return middleware_handler