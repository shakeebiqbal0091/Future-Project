from typing import Any, Dict, Optional, Union
from datetime import datetime, timedelta
import jwt
import redis
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models.models import User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
redis_client = redis.Redis.from_url(settings.REDIS_URL)

class TokenData(BaseModel):
    username: Optional[str] = None

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

class Token(BaseModel):
    access_token: str
    token_type: str

class PasswordUtils:
    @staticmethod
    def hash_password(password: str) -> str:
        return pwd_context.hash(password)

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        return pwd_context.verify(plain_password, hashed_password)

class JWTUtils:
    @staticmethod
    def create_access_token(subject: str, expires_delta: Optional[timedelta] = None) -> str:
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=15)

        to_encode = {"sub": subject, "exp": expire}
        encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        return encoded_jwt

    @staticmethod
    def create_refresh_token(subject: str, expires_delta: Optional[timedelta] = None) -> str:
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(days=30)

        to_encode = {"sub": subject, "exp": expire}
        encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        return encoded_jwt

    @staticmethod
    def verify_token(token: str) -> TokenData:
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            username: str = payload.get("sub")
            if username is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token",
                )
            return TokenData(username=username)
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
            )

class RateLimiter:
    @staticmethod
    def is_rate_limited(key: str, max_requests: int, window_seconds: int) -> bool:
        current = redis_client.incr(key)
        if current == 1:
            redis_client.expire(key, window_seconds)
        return current > max_requests

    @staticmethod
    def get_rate_limit_header(key: str, max_requests: int, window_seconds: int) -> Dict[str, str]:
        current = redis_client.get(key)
        if current is None:
            current = 0
        else:
            current = int(current)

        return {
            "X-RateLimit-Limit": str(max_requests),
            "X-RateLimit-Remaining": str(max(0, max_requests - current)),
            "X-RateLimit-Reset": str(int(redis_client.ttl(key)))
        }

class InputValidator:
    @staticmethod
    def validate_email(email: str) -> bool:
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))

    @staticmethod
    def validate_password(password: str) -> bool:
        if len(password) < 8:
            return False
        if not any(char.isdigit() for char in password):
            return False
        if not any(char.isalpha() for char in password):
            return False
        return True

    @staticmethod
    def sanitize_input(data: Dict[str, Any]) -> Dict[str, Any]:
        import html
        sanitized = {}
        for key, value in data.items():
            if isinstance(value, str):
                sanitized[key] = html.escape(value)
            else:
                sanitized[key] = value
        return sanitized

class SessionManager:
    @staticmethod
    def create_session_token(user_id: str) -> str:
        token = JWTUtils.create_access_token(user_id, timedelta(days=1))
        redis_client.setex(f"session:{user_id}", timedelta(days=1), token)
        return token

    @staticmethod
    def validate_session_token(token: str) -> Optional[str]:
        try:
            payload = JWTUtils.verify_token(token)
            user_id = payload.username
            stored_token = redis_client.get(f"session:{user_id}")
            if stored_token and stored_token.decode() == token:
                return user_id
            return None
        except:
            return None

    @staticmethod
    def invalidate_session(user_id: str) -> None:
        redis_client.delete(f"session:{user_id}")