from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from starlette.exceptions import HTTPException as StarletteHTTPException


def setup_exception_handlers(app: FastAPI):
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request, exc):
        return JSONResponse(
            status_code=422,
            content={
                "detail": "Validation error",
                "error_code": "validation_error",
                "fields": exc.errors(),
                "body": exc.body,
            },
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request, exc):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail, "error_code": "http_exception"},
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request, exc):
        return JSONResponse(
            status_code=500,
            content={
                "detail": "Internal server error",
                "error_code": "internal_error",
                "message": str(exc) if str(exc) else "An unexpected error occurred"
            },
        )


class ConflictException(Exception):
    def __init__(self, message="Conflict", status_code=409):
        self.message = message
        self.status_code = status_code


class NotFoundException(Exception):
    def __init__(self, message="Not Found", status_code=404):
        self.message = message
        self.status_code = status_code


class UnauthorizedException(Exception):
    def __init__(self, message="Unauthorized", status_code=401):
        self.message = message
        self.status_code = status_code


class ForbiddenException(Exception):
    def __init__(self, message="Forbidden", status_code=403):
        self.message = message
        self.status_code = status_code


class BadRequestException(Exception):
    def __init__(self, message="Bad Request", status_code=400):
        self.message = message
        self.status_code = status_code


class RateLimitException(Exception):
    def __init__(self, message="Rate limit exceeded", status_code=429):
        self.message = message
        self.status_code = status_code