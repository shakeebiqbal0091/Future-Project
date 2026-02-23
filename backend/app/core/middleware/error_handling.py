from fastapi import Request, Response, HTTPException
from fastapi.encoders import jsonable_encoder
from app.core.schemas.auth import ErrorResponse, ValidationErrorResponse, ValidationError
import traceback
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class ExceptionHandlerMiddleware:
    @staticmethod
    def get_error_middleware():
        async def error_middleware(request: Request, call_next):
            try:
                response: Response = await call_next(request)
                return response

            except HTTPException as http_exception:
                # Handle FastAPI HTTP exceptions
                if hasattr(http_exception, 'body') and http_exception.body:
                    return Response(
                        status_code=http_exception.status_code,
                        content=http_exception.body,
                        media_type="application/json"
                    )

                error_response = {
                    "detail": http_exception.detail,
                    "error_code": getattr(http_exception, 'error_code', None),
                    "timestamp": datetime.utcnow().isoformat()
                }

                return Response(
                    status_code=http_exception.status_code,
                    content=jsonable_encoder(error_response),
                    media_type="application/json"
                )

            except Exception as e:
                # Handle all other exceptions
                logger.error(f"Unhandled exception: {str(e)}")
                logger.error(traceback.format_exc())

                error_response = {
                    "detail": "Internal server error",
                    "error_code": "INTERNAL_SERVER_ERROR",
                    "timestamp": datetime.utcnow().isoformat()
                }

                return Response(
                    status_code=500,
                    content=jsonable_encoder(error_response),
                    media_type="application/json"
                )

        return error_middleware

class ValidationErrorMiddleware:
    @staticmethod
    def get_validation_error_middleware():
        async def validation_error_middleware(request: Request, call_next):
            try:
                response: Response = await call_next(request)
                return response
            except ValueError as e:
                raise HTTPException(
                    status_code=400,
                    detail=str(e)
                )
            except ValidationError as e:
                error_response = ValidationErrorResponse(
                    detail="Validation error",
                    errors=[
                        ValidationError(
                            field=error.loc[0] if error.loc else "body",
                            message=error.msg
                        )
                        for error in e.errors()
                    ]
                )
                raise HTTPException(
                    status_code=422,
                    detail=error_response.model_dump_json()
                )

        return validation_error_middleware