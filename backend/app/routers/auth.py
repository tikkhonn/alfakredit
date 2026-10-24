from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.db import get_session
from app.models import User
from app.schemas import LoginRequest, TokenResponse
from app.security import create_token, verify_password
from app.seed import DEMO_ACCOUNTS

router = APIRouter(tags=["auth"])


@router.post("/auth/login", response_model=TokenResponse)
def login(payload: LoginRequest, session: Annotated[Session, Depends(get_session)]) -> TokenResponse:
    user = session.exec(select(User).where(User.login == payload.login)).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Неверный логин или пароль")
    return TokenResponse(access_token=create_token(user.id, user.role))


@router.get("/auth/demo-accounts")
def demo_accounts() -> list[dict[str, str]]:
    return DEMO_ACCOUNTS
