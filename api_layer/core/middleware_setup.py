import logging
from fastapi import FastAPI
from .middleware import (
    RequestLoggingMiddleware,
    ErrorHandlingMiddleware,
    RateLimitingMiddleware,
    CORSMiddlewareWrapper
)

def setup_middleware(app: FastAPI, logger: logging.Logger = None):
    """Setup middleware for the FastAPI application."""

    # Request logging middleware
    if logger:
        app.add_middleware(RequestLoggingMiddleware, logger=logger)

    # Error handling middleware
    app.add_middleware(ErrorHandlingMiddleware, logger=logger)

    # Rate limiting middleware (100 requests per minute)
    app.add_middleware(RateLimitingMiddleware, rate_limit=100, window=60)

    # CORS middleware
    allow_origins = ["http://localhost:3000", "http://localhost:8000", "*"]
    cors_middleware = CORSMiddlewareWrapper(app, allow_origins)
    app.middleware_stack.append(cors_middleware)

    return app