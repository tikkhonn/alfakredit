from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session

from app.db import get_session
from app.deps import require_specialist
from app.domain.enums import ApplicationStatus
from app.domain.state_machine import IllegalTransitionError
from app.models import Application, Company, User
from app.schemas import ApplicationOut, QueueStats, SpecialistDecision
from app.services import list_applications, queue_stats, serialize_application, specialist_decide

router = APIRouter(tags=["specialist"])


@router.get("/specialist/stats", response_model=QueueStats)
def stats(
    user: Annotated[User, Depends(require_specialist)],
    session: Annotated[Session, Depends(get_session)],
) -> QueueStats:
    return queue_stats(session)


@router.get("/specialist/applications", response_model=list[ApplicationOut])
def queue(
    user: Annotated[User, Depends(require_specialist)],
    session: Annotated[Session, Depends(get_session)],
    only_pending: bool = Query(default=True),
) -> list[ApplicationOut]:
    items = list_applications(session, None)
    if only_pending:
        items = [item for item in items if item.status == ApplicationStatus.IN_REVIEW.value]
    result: list[ApplicationOut] = []
    for item in items:
        company = session.get(Company, item.company_id)
        result.append(serialize_application(item, "specialist", company, session))
    return result


@router.get("/specialist/applications/{application_id}", response_model=ApplicationOut)
def dossier(
    application_id: str,
    user: Annotated[User, Depends(require_specialist)],
    session: Annotated[Session, Depends(get_session)],
) -> ApplicationOut:
    application = session.get(Application, application_id)
    if not application:
        raise HTTPException(status_code=404, detail="Заявка не найдена")
    company = session.get(Company, application.company_id)
    return serialize_application(application, "specialist", company, session)


@router.post("/specialist/applications/{application_id}/decision", response_model=ApplicationOut)
def decide_endpoint(
    application_id: str,
    payload: SpecialistDecision,
    user: Annotated[User, Depends(require_specialist)],
    session: Annotated[Session, Depends(get_session)],
) -> ApplicationOut:
    application = session.get(Application, application_id)
    if not application:
        raise HTTPException(status_code=404, detail="Заявка не найдена")
    try:
        application = specialist_decide(session, application, payload)
    except IllegalTransitionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    company = session.get(Company, application.company_id)
    return serialize_application(application, "specialist", company, session)
