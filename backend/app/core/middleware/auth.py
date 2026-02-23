from fastapi import Request, Response
from app.core.security.auth_handler import AuthHandler
from app.core.config import settings
from redis import Redis
import redis

redis_client = Redis.from_url(settings.REDIS_URL)

def get_jwt_authentication_middleware():
    async def jwt_authentication_middleware(request: Request, call_next):
        # Skip authentication for open endpoints
        open_endpoints = [
            "/api/v1/auth/login",
            "/api/v1/auth/register",
            "/api/v1/auth/refresh",
            "/api/v1/auth/logout",
            "/api/v1/auth/password-reset-request",
            "/api/v1/auth/password-reset",
            "/api/v1/health",
            "/api/v1/",
        ]

        if any(request.url.path.startswith(endpoint) for endpoint in open_endpoints):
            response: Response = await call_next(request)
            return response

        # Check for token in Authorization header
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return Response(
                status_code=401,
                content={"detail": "Not authenticated"},
                media_type="application/json"
            )

        token = auth_header.split(" ")[1]

        # Check if token is blacklisted
        if AuthHandler.is_token_blacklisted(token):
            return Response(
                status_code=401,
                content={"detail": "Token has been revoked"},
                media_type="application/json"
            )

        # Verify token
        try:
            payload = AuthHandler.verify_token(token)
            username = payload.username

            # Check if user exists
            from app.core.database import get_db
            db = next(get_db())
            user = db.query(User).filter(User.username == username).first()
            if not user:
                return Response(
                    status_code=401,
                    content={"detail": "User not found"},
                    media_type="application/json"
                )

            # Set user in request state
            request.state.user = user

        except Exception as e:
            return Response(
                status_code=401,
                content={"detail": "Invalid token"},
                media_type="application/json"
            )

        response: Response = await call_next(request)
        return response

    return jwt_authentication_middleware