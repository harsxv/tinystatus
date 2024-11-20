from functools import wraps
from fastapi import HTTPException, Request, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import secrets
from typing import Optional
from .database import SessionLocal, User
from .config import get_settings

settings = get_settings()
security = HTTPBasic()


def get_current_user(credentials: HTTPBasicCredentials) -> Optional[User]:
    """Validate credentials and return user"""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == credentials.username).first()
        if user and user.check_password(credentials.password):
            return user
        return None
    finally:
        db.close()


def get_user_by_token(token: str) -> Optional[User]:
    """Get user by API token"""
    db = SessionLocal()
    try:
        return db.query(User).filter(User.api_token == token).first()
    finally:
        db.close()


def require_auth(func):
    """Decorator for routes requiring basic auth"""

    @wraps(func)
    async def wrapper(request: Request, *args, **kwargs):
        if not settings.AUTH_ENABLED:
            return await func(request, *args, **kwargs)

        credentials = await security(request)
        user = get_current_user(credentials)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
                headers={"WWW-Authenticate": "Basic"},
            )
        return await func(request, *args, **kwargs)

    return wrapper


def require_token(func):
    """Decorator for API routes requiring token auth"""

    @wraps(func)
    async def wrapper(*args, **kwargs):
        if not settings.AUTH_ENABLED:
            return await func(*args, **kwargs)

        request = kwargs.get("request") or args[0]
        token = request.headers.get("Authorization")

        if not token or not token.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing or invalid token",
                headers={"WWW-Authenticate": "Bearer"},
            )

        token = token.split(" ")[1]
        user = get_user_by_token(token)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return await func(*args, **kwargs)

    return wrapper
