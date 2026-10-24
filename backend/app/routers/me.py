from typing import Annotated

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.db import get_session
from app.deps import get_current_user
from app.models import Company, User
from app.schemas import UserOut
from app.services import company_out

router = APIRouter(tags=["me"])


@router.get("/me", response_model=UserOut)
def me(
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> UserOut:
    company = session.get(Company, user.company_id) if user.company_id else None
    return UserOut(
        id=user.id,
        login=user.login,
        full_name=user.full_name,
        role=user.role,
        company=company_out(company, session) if company else None,
    )
