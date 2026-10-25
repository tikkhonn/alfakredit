from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from app.adapters.registry import MockRegistry
from app.db import get_session
from app.deps import get_registry, require_client
from app.domain.state_machine import IllegalTransitionError
from app.models import Application, Company, User
from app.schemas import (
    ApplicationCreate,
    ApplicationOut,
    ExtraSubmit,
    RecommendRequest,
    RecommendResponse,
    SignRequest,
    WhatIfRequest,
)
from app.services import (
    OpenApplicationError,
    accept_offer,
    apply_what_if,
    create_application,
    cure_tax_arrears,
    decline_offer,
    list_applications,
    recommend,
    serialize_application,
    sign_offer,
    submit_extra,
)

router = APIRouter(tags=["client"])


def _company(user: User, session: Session) -> Company:
    company = session.get(Company, user.company_id) if user.company_id else None
    if not company:
        raise HTTPException(status_code=400, detail="Компания не загружена")
    return company


@router.post("/recommend", response_model=RecommendResponse)
def recommend_endpoint(
    payload: RecommendRequest,
    user: Annotated[User, Depends(require_client)],
    session: Annotated[Session, Depends(get_session)],
) -> RecommendResponse:
    return recommend(_company(user, session), payload, session)


@router.get("/applications", response_model=list[ApplicationOut])
def list_mine(
    user: Annotated[User, Depends(require_client)],
    session: Annotated[Session, Depends(get_session)],
) -> list[ApplicationOut]:
    company = _company(user, session)
    return [
        serialize_application(item, "client", company, session)
        for item in list_applications(session, company.id)
    ]


@router.post("/applications", response_model=ApplicationOut)
def create_mine(
    payload: ApplicationCreate,
    user: Annotated[User, Depends(require_client)],
    session: Annotated[Session, Depends(get_session)],
    registry: Annotated[MockRegistry, Depends(get_registry)],
) -> ApplicationOut:
    company = _company(user, session)
    try:
        application = create_application(session, company, user.id, payload, registry)
    except OpenApplicationError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return serialize_application(application, "client", company, session)


@router.get("/applications/{application_id}", response_model=ApplicationOut)
def get_mine(
    application_id: str,
    user: Annotated[User, Depends(require_client)],
    session: Annotated[Session, Depends(get_session)],
) -> ApplicationOut:
    application = session.get(Application, application_id)
    if not application or application.company_id != user.company_id:
        raise HTTPException(status_code=404, detail="Заявка не найдена")
    return serialize_application(application, "client", _company(user, session), session)


@router.post("/applications/{application_id}/extra", response_model=ApplicationOut)
def extra_mine(
    application_id: str,
    payload: ExtraSubmit,
    user: Annotated[User, Depends(require_client)],
    session: Annotated[Session, Depends(get_session)],
    registry: Annotated[MockRegistry, Depends(get_registry)],
) -> ApplicationOut:
    application = session.get(Application, application_id)
    if not application or application.company_id != user.company_id:
        raise HTTPException(status_code=404, detail="Заявка не найдена")
    try:
        application = submit_extra(session, application, payload, registry)
    except IllegalTransitionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return serialize_application(application, "client", _company(user, session), session)


@router.post("/applications/{application_id}/accept", response_model=ApplicationOut)
def accept_mine(
    application_id: str,
    user: Annotated[User, Depends(require_client)],
    session: Annotated[Session, Depends(get_session)],
) -> ApplicationOut:
    application = session.get(Application, application_id)
    if not application or application.company_id != user.company_id:
        raise HTTPException(status_code=404, detail="Заявка не найдена")
    try:
        application = accept_offer(session, application)
    except IllegalTransitionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return serialize_application(application, "client", _company(user, session), session)


@router.post("/applications/{application_id}/decline", response_model=ApplicationOut)
def decline_mine(
    application_id: str,
    user: Annotated[User, Depends(require_client)],
    session: Annotated[Session, Depends(get_session)],
) -> ApplicationOut:
    application = session.get(Application, application_id)
    if not application or application.company_id != user.company_id:
        raise HTTPException(status_code=404, detail="Заявка не найдена")
    try:
        application = decline_offer(session, application)
    except IllegalTransitionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return serialize_application(application, "client", _company(user, session), session)


@router.post("/applications/{application_id}/sign", response_model=ApplicationOut)
def sign_mine(
    application_id: str,
    payload: SignRequest,
    user: Annotated[User, Depends(require_client)],
    session: Annotated[Session, Depends(get_session)],
) -> ApplicationOut:
    application = session.get(Application, application_id)
    if not application or application.company_id != user.company_id:
        raise HTTPException(status_code=404, detail="Заявка не найдена")
    try:
        application = sign_offer(session, application, payload.code)
    except IllegalTransitionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return serialize_application(application, "client", _company(user, session), session)


@router.post("/applications/{application_id}/cure", response_model=ApplicationOut)
def cure_mine(
    application_id: str,
    user: Annotated[User, Depends(require_client)],
    session: Annotated[Session, Depends(get_session)],
    registry: Annotated[MockRegistry, Depends(get_registry)],
) -> ApplicationOut:
    application = session.get(Application, application_id)
    if not application or application.company_id != user.company_id:
        raise HTTPException(status_code=404, detail="Заявка не найдена")
    try:
        application = cure_tax_arrears(session, application, registry)
    except IllegalTransitionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return serialize_application(application, "client", _company(user, session), session)


@router.post("/applications/{application_id}/what-if", response_model=ApplicationOut)
def what_if_mine(
    application_id: str,
    payload: WhatIfRequest,
    user: Annotated[User, Depends(require_client)],
    session: Annotated[Session, Depends(get_session)],
    registry: Annotated[MockRegistry, Depends(get_registry)],
) -> ApplicationOut:
    application = session.get(Application, application_id)
    if not application or application.company_id != user.company_id:
        raise HTTPException(status_code=404, detail="Заявка не найдена")
    try:
        application = apply_what_if(session, application, payload.action, registry)
    except IllegalTransitionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return serialize_application(application, "client", _company(user, session), session)
