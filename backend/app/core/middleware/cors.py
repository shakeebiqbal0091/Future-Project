from fastapi import Request, Response
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings

def get_cors_middleware() -> CORSMiddleware:
    return CORSMiddleware(
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=settings.ALLOWED_METHODS,
        allow_headers=settings.ALLOWED_HEADERS,
        allow_wildcard_origins=False,
        allow_preflight=True,
    )

def add_security_headers_middleware():
    async def security_headers_middleware(request: Request, call_next):
        response: Response = await call_next(request)

        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self' https:; "
            "connect-src 'self' https:; "
            "frame-ancestors 'none';"
        )

        # Set security cookies
        if 'set-cookie' in response.headers:
            cookies = response.headers['set-cookie'].split(',')
            secure_cookies = []
            for cookie in cookies:
                if 'HttpOnly' not in cookie:
                    cookie += '; HttpOnly'
                if 'Secure' not in cookie and not settings.DEBUG:
                    cookie += '; Secure'
                if 'SameSite' not in cookie:
                    cookie += '; SameSite=Strict'
                secure_cookies.append(cookie.strip())
            response.headers['set-cookie'] = ', '.join(secure_cookies)

        return response

    return security_headers_middleware