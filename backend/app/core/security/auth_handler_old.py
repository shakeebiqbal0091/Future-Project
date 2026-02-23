from typing import Any, Dict, Optional, Union
from datetime import datetime, timedelta
import jwt
from passlib.context import CryptContext
from jose import JWTError, jwt
from fastapi import HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy.orm import Session
from redis import Redis
import redis
from app.core.config import settings
from app.models.models import User
from app.core.database import engine
from app.core.security.utils import PasswordUtils, JWTUtils, RateLimiter, InputValidator
from app.core.security.utils import TokenData, Token

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")
redis_client = Redis.from_url(settings.REDIS_URL)


class AuthHandler:
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        return pwd_context.verify(plain_password, hashed_password)

    @staticmethod
    def get_password_hash(password: str) -> str:
        return pwd_context.hash(password)

    @staticmethod
    def authenticate_user(db: Session, username: str, password: str) -> Optional[User]:
        user = db.query(User).filter(User.username == username).first()
        if not user:
            return None
        if not PasswordUtils.verify_password(password, user.hashed_password):
            return None
        return user

    @staticmethod
    def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
        return JWTUtils.create_access_token(data, expires_delta)

    @staticmethod
    def create_refresh_token(data: dict, expires_delta: Optional[timedelta] = None):
        return JWTUtils.create_refresh_token(data, expires_delta)

    @staticmethod
    async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends()) -> User:
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            username: str = payload.get("sub")
            if username is None:
                raise credentials_exception
            token_data = TokenData(username=username)
        except JWTError:
            raise credentials_exception

        user = db.query(User).filter(User.username == token_data.username).first()
        if user is None:
            raise credentials_exception
        return user

    @staticmethod
    async def get_current_active_user(current_user: User = Depends(AuthHandler.get_current_user)) -> User:
        if not current_user.is_active:
            raise HTTPException(status_code=400, detail="Inactive user")
        return current_user

    @staticmethod
    def blacklist_token(token: str) -> None:
        redis_client.setex(token, timedelta(minutes=15), "blacklisted")

    @staticmethod
    def is_token_blacklisted(token: str) -> bool:
        return redis_client.exists(token) == 1