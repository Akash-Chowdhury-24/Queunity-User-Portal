from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
from fastapi import Request
from jose import JWTError, jwt

from app.core.config import settings
from app.core.exceptions import APIException

def _password_bytes(password: str) -> bytes:
    return password.encode("utf-8")


def hash_password(password: str) -> str:
    return bcrypt.hashpw(_password_bytes(password), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(
        _password_bytes(plain_password), hashed_password.encode("utf-8")
    )


def create_access_token(subject: dict) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload = subject.copy()
    payload.update({"exp": expire})
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def verify_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(
            token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM]
        )
    except JWTError as exc:
        raise APIException(status_code=401, message="Invalid token") from exc



async def get_token_from_header(auth_header: str | None) -> str:
    if not auth_header or not auth_header.startswith("Bearer "):
        raise APIException(status_code=401, message="Unauthorized no token provided")

    token = auth_header[len("Bearer ") :].strip()
    if not token:
        raise APIException(status_code=401, message="Not authenticated")

    return token


async def get_bearer_token_from_request(request: Request) -> str:
    return await get_token_from_header(request.headers.get("Authorization"))
