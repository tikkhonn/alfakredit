from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlmodel import Session

from app.adapters.registry import MockRegistry
from app.db import get_session
from app.models import User
from app.seed import build_registry
from app.security import decode_token

bearer = HTTPBearer(auto_error=False)
REGISTRY = build_registry()


def get_registry() -> MockRegistry:
    return REGISTRY


def get_current_user(
    session: Annotated[Session, Depends(get_session)],
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> User:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Нужна авторизация")
    try:
        payload = decode_token(credentials.credentials)
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Сессия истекла") from exc
    user = session.get(User, payload.get("sub"))
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Пользователь не найден")
    return user


def require_client(user: Annotated[User, Depends(get_current_user)]) -> User:
    if user.role != "client":
        raise HTTPException(status_code=403, detail="Этот экран только для клиента")
    if not user.company_id:
        raise HTTPException(status_code=400, detail="У клиента нет компании")
    return user


def require_specialist(user: Annotated[User, Depends(get_current_user)]) -> User:
    if user.role != "specialist":
        raise HTTPException(status_code=403, detail="Этот экран только для специалиста")
    return user
