from fastapi import Request, Response
from app.core.security.utils import RateLimiter
from app.core.config import settings
import redis
from typing import Dict, Optional

redis_client = redis.Redis.from_url(settings.REDIS_URL)

def get_rate_limiting_middleware():
    async def rate_limiting_middleware(request: Request, call_next):
        # Define rate limits for different endpoints
        rate_limits = {
            # Authentication endpoints
            "/api/v1/auth/login": {"max_requests": 10, "window_seconds": 900},  # 10 requests per 15 minutes
            "/api/v1/auth/register": {"max_requests": 5, "window_seconds": 3600},  # 5 requests per hour
            "/api/v1/auth/refresh": {"max_requests": 30, "window_seconds": 3600},  # 30 requests per hour
            "/api/v1/auth/password-reset-request": {"max_requests": 3, "window_seconds": 3600},  # 3 requests per hour
            "/api/v1/auth/password-reset": {"max_requests": 3, "window_seconds": 3600},  # 3 requests per hour

            # User endpoints
            "/api/v1/auth/me": {"max_requests": 100, "window_seconds": 3600},  # 100 requests per hour
            "/api/v1/users": {"max_requests": 100, "window_seconds": 3600},  # 100 requests per hour

            # Agent endpoints
            "/api/v1/agents": {"max_requests": 100, "window_seconds": 3600},  # 100 requests per hour
            "/api/v1/agents/*": {"max_requests": 100, "window_seconds": 3600},  # 100 requests per hour

            # Workflow endpoints
            "/api/v1/workflows": {"max_requests": 100, "window_seconds": 3600},  # 100 requests per hour
            "/api/v1/workflows/*": {"max_requests": 100, "window_seconds": 3600},  # 100 requests per hour

            # Task endpoints
            "/api/v1/tasks": {"max_requests": 100, "window_seconds": 3600},  # 100 requests per hour
            "/api/v1/tasks/*": {"max_requests": 100, "window_seconds": 3600},  # 100 requests per hour
        }

        # Get the specific rate limit for this endpoint
        endpoint = request.url.path
        rate_limit_config = rate_limits.get(endpoint) or rate_limits.get(endpoint.rstrip("0123456789"))

        if not rate_limit_config:
            # Default rate limit for other endpoints
            rate_limit_config = {"max_requests": 200, "window_seconds": 3600}

        max_requests = rate_limit_config["max_requests"]
        window_seconds = rate_limit_config["window_seconds"]

        # Create rate limit key
        rate_limit_key = f"rate_limit:{endpoint}:{request.client.host}"

        # Check if rate limited
        if RateLimiter.is_rate_limited(rate_limit_key, max_requests, window_seconds):
            return Response(
                status_code=429,
                content={"detail": "Too many requests"},
                media_type="application/json"
            )

        # Get rate limit headers
        rate_limit_headers = RateLimiter.get_rate_limit_header(rate_limit_key, max_requests, window_seconds)

        response: Response = await call_next(request)

        # Add rate limit headers to response
        for header, value in rate_limit_headers.items():
            response.headers[header] = str(value)

        return response

    return rate_limiting_middleware