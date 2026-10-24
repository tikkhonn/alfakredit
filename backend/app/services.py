from __future__ import annotations

from datetime import date
from statistics import mean

from sqlalchemy.orm import selectinload
from sqlmodel import Session, col, select

from app.adapters.registry import MockRegistry
from app.config import settings
from app.demo_state import get_chaos
from app.domain.conveyor import OUTCOME_EVENT_COPY, decide, policy_to_dict, scoring_to_dict
from app.domain.enums import (
    Actor,
    ApplicationStatus,
    CLIENT_STATUS_LABELS,
    ProductCode,
    PurposeCode,
)
from app.domain.finance import (
    dscr,
    extra_turnover_for_request,
    monthly_payment,
    payment_schedule,
    round_amount,
)
from app.domain.policy import Enrichment, rate_from_score
from app.domain.products import PRODUCTS, PURPOSE_COPY, kassa_limit, recommend_product
from app.domain.scoring import ScoringInput, ScoringResult, score
from app.domain.state_machine import ACTION_ACTORS, IllegalTransitionError, can, next_status
from app.models import Application, ApplicationEvent, Company, utcnow
from app.schemas import (
    ApplicationCreate,
    ApplicationOut,
    CompanyOut,
    EventOut,
    ExtraSubmit,
    RecommendRequest,
    RecommendResponse,
    SpecialistDecision,
)

ACTIVE_DEBT_STATUSES = {ApplicationStatus.ISSUED.value, ApplicationStatus.SIGNING.value}


def _age_months(registered_at: date, today: date | None = None) -> int:
    today = today or date.today()
    return max(0, (today.year - registered_at.year) * 12 + today.month - registered_at.month)


def _tax_cured(session: Session, application_id: str) -> bool:
    statement = select(ApplicationEvent).where(
        ApplicationEvent.application_id == application_id,
        ApplicationEvent.action == "cure_restart",
    )
    return session.exec(statement).first() is not None


def issued_exposure(session: Session, company_id: str, *, product: str | None = None, exclude_id: str | None = None) -> int:
    statement = select(Application).where(
        Application.company_id == company_id,
        col(Application.status).in_(ACTIVE_DEBT_STATUSES),
    )
    if product:
        statement = statement.where(Application.product == product)
    total = 0
    for item in session.exec(statement).all():
        if exclude_id and item.id == exclude_id:
            continue
        total += item.offer_amount or 0
    return total


def company_out(company: Company, session: Session | None = None) -> CompanyOut:
    avg = int(mean(company.turnovers)) if company.turnovers else 0
    ceiling = kassa_limit(avg)
    issued = issued_exposure(session, company.id, product=ProductCode.KASSA.value) if session else 0
    return CompanyOut(
        id=company.id,
        legal_form=company.legal_form,
        inn=company.inn,
        ogrn=company.ogrn,
        name=company.name,
        short_name=company.short_name,
        okved=company.okved,
        okved_name=company.okved_name,
        registered_at=company.registered_at,
        status=company.status,
        director_name=company.director_name,
        account_blocked=company.account_blocked,
        turnovers=company.turnovers,
        avg_turnover=avg,
        kassa_limit=max(0, ceiling - issued),
        kassa_ceiling=ceiling,
        issued_kassa=issued,
        business_age_months=_age_months(company.registered_at),
    )


def build_enrichment(
    company: Company,
    registry: MockRegistry,
    application: Application,
    session: Session,
    missing: list[str] | None = None,
) -> Enrichment:
    egrul = registry.egrul(company.inn)
    fns = registry.fns(company.inn)
    chaos = get_chaos()
    if chaos["bki_down"]:
        bki_overdue = 0
        bki_debt = 0
        bki_inquiries = 0
    else:
        bki = registry.bki(company.inn)
        bki_overdue = bki.overdue_days
        bki_debt = bki.current_debt
        bki_inquiries = bki.inquiries_90d
    return Enrichment(
        legal_status=egrul.status,
        tax_arrears=fns.tax_arrears,
        account_blocked=company.account_blocked,
        bki_overdue_days=bki_overdue,
        bki_current_debt=bki_debt,
        bki_inquiries_90d=bki_inquiries,
        turnovers=list(company.turnovers),
        business_age_months=_age_months(company.registered_at),
        missing_fields=missing or [],
        extra_turnover=application.extra_turnover,
        issued_kassa=issued_exposure(session, company.id, product=ProductCode.KASSA.value, exclude_id=application.id),
        issued_debt=issued_exposure(session, company.id, exclude_id=application.id),
        profile_changed=application.profile_changed,
        bki_unavailable=chaos["bki_down"],
        collateral_msp=application.collateral_msp,
        tax_cured=_tax_cured(session, application.id),
    )


def enrichment_snapshot(company: Company, registry: MockRegistry, enrichment: Enrichment) -> dict:
    egrul = registry.egrul(company.inn)
    fns = registry.fns(company.inn)
    snapshot = {
        "egrul": {
            "source": "mock://egrul",
            "inn": egrul.inn,
            "ogrn": egrul.ogrn,
            "status": egrul.status,
            "okved": egrul.okved,
            "registered_at": egrul.registered_at.isoformat(),
        },
        "fns": {
            "source": "mock://fns-transparent-business",
            "tax_arrears": fns.tax_arrears,
            "arrears_amount": fns.arrears_amount,
        },
        "account_blocked": enrichment.account_blocked,
        "turnovers": enrichment.turnovers,
        "business_age_months": enrichment.business_age_months,
        "missing_fields": enrichment.missing_fields,
        "extra_turnover": enrichment.extra_turnover,
        "issued_kassa": enrichment.issued_kassa,
        "issued_debt": enrichment.issued_debt,
    }
    if enrichment.bki_unavailable:
        snapshot["bki"] = {
            "source": "mock://bki",
            "status": "timeout",
            "overdue_days": 0,
            "current_debt": 0,
            "inquiries_90d": 0,
            "worst_status": "unavailable",
        }
    else:
        bki = registry.bki(company.inn)
        snapshot["bki"] = {
            "source": "mock://bki",
            "status": "ok",
            "overdue_days": bki.overdue_days,
            "current_debt": bki.current_debt,
            "inquiries_90d": bki.inquiries_90d,
            "worst_status": bki.worst_status,
        }
    return snapshot


def build_pipeline(enrichment: Enrichment, fns_amount: int) -> list[dict]:
    bki_status = "timeout" if enrichment.bki_unavailable else "ok"
    policy_status = "fallback" if enrichment.bki_unavailable else "ok"
    fns_status = "arrears" if enrichment.tax_arrears else "ok"
    return [
        {"code": "validation", "title": "Валидация заявки", "ms": 12, "status": "ok", "detail": "Сумма, срок, роль клиента"},
        {"code": "abs", "title": "АБС / ПДН", "ms": 15, "status": "ok", "detail": "Карточка клиента из банка"},
        {"code": "egrul", "title": "ЕГРЮЛ / ЕГРИП", "ms": 38, "status": "ok", "detail": enrichment.legal_status},
        {
            "code": "fns",
            "title": "ФНС",
            "ms": 57,
            "status": fns_status,
            "detail": f"долг {fns_amount:,} ₽".replace(",", " ") if enrichment.tax_arrears else "недоимки нет",
        },
        {
            "code": "bki",
            "title": "БКИ",
            "ms": 180 if enrichment.bki_unavailable else 92,
            "status": bki_status,
            "detail": "таймаут, включён circuit breaker" if enrichment.bki_unavailable else "история получена",
        },
        {
            "code": "policy",
            "title": "Скоринг и политика",
            "ms": 9,
            "status": policy_status,
            "detail": "балл 0–100 отдельно от правил",
        },
    ]


def risk_memo(application: Application, company: Company) -> str:
    scoring = application.scoring or {}
    policy = application.policy or {}
    factors = scoring.get("factors") or []
    lines = [
        f"{company.short_name}, ИНН {company.inn}, {company.okved} {company.okved_name}.",
        f"Запрос {application.requested_amount:,} ₽ на {application.requested_term_months} мес. по продукту «{PRODUCTS[ProductCode(application.product)].name}».".replace(",", " "),
    ]
    if application.purpose_details:
        lines.append(f"Цель: {application.purpose_details}.")
    total = scoring.get("total")
    if total is not None:
        lines.append(f"Скоринг {total}/100 ({scoring.get('band')}). Это подсказка, не решение.")
    weak = [factor["title"] for factor in factors if factor.get("points", 0) < factor.get("max_points", 1) / 2]
    if weak:
        lines.append("Слабые места: " + ", ".join(weak) + ".")
    rules = policy.get("rules") or []
    if rules:
        lines.append("Путь правил: " + " → ".join(str(rule) for rule in rules) + ".")
    summary = policy.get("specialist_summary")
    if summary:
        lines.append(str(summary))
    return " ".join(lines)


def _next_public_number(session: Session) -> str:
    count = len(session.exec(select(Application)).all())
    return f"APP-2026-{count + 1:04d}"


def add_event(
    session: Session,
    application: Application,
    action: str,
    message: str,
    detail: dict | None = None,
) -> None:
    session.add(
        ApplicationEvent(
            application_id=application.id,
            actor=ACTION_ACTORS.get(action, Actor.SYSTEM).value,
            action=action,
            status=application.status,
            message=message,
            detail=detail or {},
        )
    )


def run_automatic_pass(session: Session, application: Application, registry: MockRegistry) -> Application:
    company = session.get(Company, application.company_id)
    if not company:
        raise ValueError("Компания не найдена")
    missing: list[str] = []
    if application.product == ProductCode.RAZVITIE.value and not (application.purpose_details or "").strip():
        missing.append("purpose_details")
    enrichment = build_enrichment(company, registry, application, session, missing)
    scoring, decision, action = decide(
        product_code=ProductCode(application.product),
        requested_amount=application.requested_amount,
        requested_term_months=application.requested_term_months,
        enrichment=enrichment,
        key_rate=settings.key_rate,
    )
    fns_amount = registry.fns(company.inn).arrears_amount
    application.enrichment = enrichment_snapshot(company, registry, enrichment)
    application.scoring = scoring_to_dict(scoring)
    application.policy = policy_to_dict(decision)
    application.pipeline = build_pipeline(enrichment, fns_amount)
    application.client_message = decision.client_message
    application.offer_amount = decision.offered_amount
    application.offer_term_months = decision.offered_term_months
    application.offer_rate = decision.rate_annual
    application.extra_fields = decision.extra_fields
    application.decided_by = "system"
    application.status = next_status(ApplicationStatus(application.status), action).value
    application.updated_at = utcnow()
    add_event(
        session,
        application,
        action,
        OUTCOME_EVENT_COPY[decision.outcome],
        {"rules": decision.rules, "specialist_summary": decision.specialist_summary},
    )
    session.add(application)
    return application


def recommend(company: Company, payload: RecommendRequest, session: Session) -> RecommendResponse:
    product = recommend_product(payload.purpose)
    copy = PURPOSE_COPY[payload.purpose]
    avg = int(mean(company.turnovers)) if company.turnovers else 0
    issued = issued_exposure(session, company.id, product=ProductCode.KASSA.value)
    available = max(0, kassa_limit(avg) - issued)
    if payload.amount:
        amount = round_amount(payload.amount)
    elif product.code == ProductCode.KASSA:
        amount = round_amount(min(available or product.min_amount, max(product.min_amount, avg // 3)))
    else:
        amount = round_amount(min(product.max_amount, max(product.min_amount, avg * 2)))
    term = payload.term_months or (6 if product.code == ProductCode.KASSA else 24)
    scoring = score(
        ScoringInput(
            business_age_months=_age_months(company.registered_at),
            turnovers=list(company.turnovers),
            requested_amount=amount,
            bki_overdue_days=0,
            bki_current_debt=0,
            bki_inquiries_90d=0,
            issued_debt=issued_exposure(session, company.id),
        )
    )
    rate = rate_from_score(settings.key_rate, scoring)
    return RecommendResponse(
        purpose=payload.purpose,
        purpose_title=copy["title"],
        purpose_subtitle=copy["subtitle"],
        why=copy["why"],
        product=product.code,
        product_name=product.name,
        product_tagline=product.tagline,
        suggested_amount=amount,
        suggested_term_months=term,
        min_amount=product.min_amount,
        max_amount=product.max_amount,
        min_term_months=product.min_term_months,
        max_term_months=product.max_term_months,
        kassa_limit=available if product.code == ProductCode.KASSA else None,
        monthly_payment=monthly_payment(amount, rate, term),
        indicative_rate=rate,
    )


def create_application(
    session: Session,
    company: Company,
    user_id: str,
    payload: ApplicationCreate,
    registry: MockRegistry,
) -> Application:
    product = PRODUCTS[payload.product]
    application = Application(
        public_number=_next_public_number(session),
        company_id=company.id,
        created_by_user_id=user_id,
        purpose=payload.purpose.value,
        product=payload.product.value,
        requested_amount=round_amount(payload.requested_amount),
        requested_term_months=payload.requested_term_months,
        purpose_details=payload.purpose_details,
        profile_changed=payload.profile_changed,
        status=ApplicationStatus.SUBMITTED.value,
        extra_fields=[],
        pipeline=[],
    )
    session.add(application)
    session.flush()
    add_event(
        session,
        application,
        "submit",
        f"Клиент отправил заявку на «{product.name}»",
        {"purpose": payload.purpose.value, "amount": application.requested_amount},
    )
    run_automatic_pass(session, application, registry)
    session.commit()
    session.refresh(application)
    return application


def submit_extra(
    session: Session,
    application: Application,
    payload: ExtraSubmit,
    registry: MockRegistry,
) -> Application:
    if application.status != ApplicationStatus.EXTRA_REQUESTED.value:
        raise IllegalTransitionError("Сейчас уточнения не требуются")
    if payload.purpose_details is not None:
        application.purpose_details = payload.purpose_details
    if payload.requested_amount is not None:
        application.requested_amount = round_amount(payload.requested_amount)
    if payload.requested_term_months is not None:
        application.requested_term_months = payload.requested_term_months
    application.extra_comment = None
    application.status = next_status(ApplicationStatus.EXTRA_REQUESTED, "client_extra").value
    application.updated_at = utcnow()
    add_event(session, application, "client_extra", "Клиент дополнил заявку")
    run_automatic_pass(session, application, registry)
    session.commit()
    session.refresh(application)
    return application


def accept_offer(session: Session, application: Application) -> Application:
    action = "client_accept"
    application.status = next_status(ApplicationStatus(application.status), action).value
    application.updated_at = utcnow()
    add_event(session, application, action, "Клиент принял условия")
    session.add(application)
    session.commit()
    session.refresh(application)
    return application


def decline_offer(session: Session, application: Application) -> Application:
    action = "client_decline"
    application.status = next_status(ApplicationStatus(application.status), action).value
    application.updated_at = utcnow()
    application.client_message = "Вы отказались от предложения. Чтобы попробовать снова, откройте новую заявку."
    add_event(session, application, action, "Клиент отказался от предложения")
    session.add(application)
    session.commit()
    session.refresh(application)
    return application


def sign_offer(session: Session, application: Application, code: str) -> Application:
    if code != settings.sign_code:
        raise ValueError("Неверный код подтверждения")
    action = "client_sign"
    application.status = next_status(ApplicationStatus(application.status), action).value
    application.updated_at = utcnow()
    application.client_message = "Договор подписан. Сумма зачислена на расчётный счёт."
    add_event(session, application, action, "Документы подписаны, выдача смоделирована")
    session.add(application)
    session.commit()
    session.refresh(application)
    return application


def cure_tax_arrears(session: Session, application: Application, registry: MockRegistry) -> Application:
    if application.status != ApplicationStatus.REJECTED.value:
        raise IllegalTransitionError("Погашение недоимки доступно только после отказа")
    rules = list((application.policy or {}).get("rules") or [])
    if "stop:tax_arrears" not in rules:
        raise IllegalTransitionError("Стоп-фактор по налогам не срабатывал")
    company = session.get(Company, application.company_id)
    if not company:
        raise ValueError("Компания не найдена")
    registry.cure_tax(company.inn)
    application.status = next_status(ApplicationStatus.REJECTED, "cure_restart").value
    application.updated_at = utcnow()
    add_event(session, application, "cure_restart", "Клиент смоделировал погашение налога")
    session.flush()
    run_automatic_pass(session, application, registry)
    session.commit()
    session.refresh(application)
    return application


def apply_what_if(session: Session, application: Application, action: str, registry: MockRegistry) -> Application:
    if application.status != ApplicationStatus.COUNTEROFFER.value:
        raise IllegalTransitionError("Пересчёт доступен на встречных условиях")
    company = session.get(Company, application.company_id)
    if not company:
        raise ValueError("Компания не найдена")
    avg = int(mean(company.turnovers)) if company.turnovers else 0
    issued = issued_exposure(session, company.id, product=ProductCode.KASSA.value, exclude_id=application.id)
    if action == "other_bank":
        application.extra_turnover = extra_turnover_for_request(avg, issued, application.requested_amount)
        application.collateral_msp = False
        message = "Клиент подгрузил выписку из другого банка"
    elif action == "msp_collateral":
        application.collateral_msp = True
        message = "Клиент готов оформить поручительство МСП"
    else:
        raise ValueError("Неизвестный сценарий пересчёта")
    application.status = next_status(ApplicationStatus.COUNTEROFFER, "what_if").value
    application.updated_at = utcnow()
    add_event(session, application, "what_if", message, {"what_if": action})
    session.flush()
    run_automatic_pass(session, application, registry)
    session.commit()
    session.refresh(application)
    return application


def specialist_decide(
    session: Session,
    application: Application,
    payload: SpecialistDecision,
) -> Application:
    mapping = {
        "offer": "specialist_offer",
        "counteroffer": "specialist_counteroffer",
        "reject": "specialist_reject",
        "extra_request": "specialist_extra",
    }
    if payload.action not in mapping:
        raise ValueError("Неизвестное действие специалиста")
    action = mapping[payload.action]
    if application.status != ApplicationStatus.IN_REVIEW.value:
        raise IllegalTransitionError("Заявка не в очереди специалиста")

    if payload.action in {"offer", "counteroffer"}:
        amount = round_amount(payload.amount or application.requested_amount)
        term = payload.term_months or application.requested_term_months
        rate = payload.rate_annual if payload.rate_annual is not None else 25.5
        application.offer_amount = amount
        application.offer_term_months = term
        application.offer_rate = rate
        if payload.action == "offer":
            application.client_message = "Специалист подтвердил условия."
        else:
            application.client_message = (
                f"Специалист готов выдать {amount:,} ₽ на {term} мес. под {rate}%.".replace(",", " ")
            )
    elif payload.action == "reject":
        application.client_message = payload.reject_reason or "По этой заявке банк не может выдать кредит."
        application.offer_amount = None
        application.offer_term_months = None
        application.offer_rate = None
    else:
        application.extra_fields = payload.extra_fields or ["purpose_details"]
        application.extra_comment = payload.extra_comment or "Уточните, на что пойдут деньги."
        application.client_message = application.extra_comment

    application.decided_by = "specialist"
    application.status = next_status(ApplicationStatus.IN_REVIEW, action).value
    application.updated_at = utcnow()
    policy = dict(application.policy or {})
    policy["specialist_action"] = payload.action
    policy["rules"] = list(policy.get("rules") or []) + [f"specialist:{payload.action}"]
    application.policy = policy
    add_event(
        session,
        application,
        action,
        {
            "offer": "Специалист подтвердил предложение",
            "counteroffer": "Специалист предложил другие условия",
            "reject": "Специалист отклонил заявку",
            "extra_request": "Специалист запросил уточнения",
        }[payload.action],
        payload.model_dump(),
    )
    session.add(application)
    session.commit()
    session.refresh(application)
    return application


def _client_actions(application: Application) -> list[str]:
    status = ApplicationStatus(application.status)
    actions: list[str] = []
    if can(status, "client_extra"):
        actions.append("submit_extra")
    if can(status, "client_accept"):
        actions.append("accept")
        actions.append("decline")
    if can(status, "client_sign"):
        actions.append("sign")
        actions.append("preview")
    if can(status, "cure_restart") and "stop:tax_arrears" in list((application.policy or {}).get("rules") or []):
        actions.append("cure")
    if can(status, "what_if"):
        actions.append("what_if")
    return actions


def _specialist_actions(application: Application) -> list[str]:
    if application.status == ApplicationStatus.IN_REVIEW.value:
        return ["offer", "counteroffer", "extra_request", "reject"]
    return []


def serialize_application(
    application: Application,
    role: str,
    include_company: Company | None = None,
    session: Session | None = None,
) -> ApplicationOut:
    events = sorted(application.events, key=lambda item: item.at)
    show_internal = role == "specialist"
    company = include_company
    amount = application.offer_amount or application.requested_amount
    term = application.offer_term_months or application.requested_term_months
    rate = application.offer_rate
    if rate is None and application.scoring and application.scoring.get("total") is not None:
        rate = rate_from_score(
            settings.key_rate,
            ScoringResult(total=int(application.scoring["total"]), max_total=100),
        )
    payment = monthly_payment(amount, rate, term) if rate else None
    avg = int(mean(company.turnovers)) if company and company.turnovers else 0
    return ApplicationOut(
        id=application.id,
        public_number=application.public_number,
        purpose=application.purpose,
        product=application.product,
        requested_amount=application.requested_amount,
        requested_term_months=application.requested_term_months,
        purpose_details=application.purpose_details,
        status=application.status,
        status_label=CLIENT_STATUS_LABELS[ApplicationStatus(application.status)],
        client_message=application.client_message,
        offer_amount=application.offer_amount,
        offer_term_months=application.offer_term_months,
        offer_rate=application.offer_rate,
        monthly_payment=payment,
        extra_fields=application.extra_fields or [],
        extra_comment=application.extra_comment,
        decided_by=application.decided_by,
        profile_changed=application.profile_changed,
        extra_turnover=application.extra_turnover,
        collateral_msp=application.collateral_msp,
        created_at=application.created_at,
        updated_at=application.updated_at,
        company=company_out(company, session) if company else None,
        events=[
            EventOut(
                id=event.id,
                at=event.at,
                actor=event.actor,
                action=event.action,
                status=event.status,
                message=event.message,
                detail=event.detail if show_internal else None,
            )
            for event in events
        ],
        scoring=application.scoring if show_internal else None,
        policy=application.policy if show_internal else None,
        enrichment=application.enrichment if show_internal else None,
        pipeline=application.pipeline or [],
        available_actions=_specialist_actions(application) if show_internal else _client_actions(application),
        dscr=dscr(avg, company.okved, payment) if show_internal and company and payment else None,
        risk_memo=risk_memo(application, company) if show_internal and company else None,
        schedule=payment_schedule(amount, rate, term) if rate else [],
    )


def list_applications(session: Session, company_id: str | None) -> list[Application]:
    statement = select(Application).options(selectinload(Application.events))
    if company_id:
        statement = statement.where(Application.company_id == company_id)
    statement = statement.order_by(col(Application.created_at).desc())
    return list(session.exec(statement).all())
