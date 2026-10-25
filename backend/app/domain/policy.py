from __future__ import annotations

from dataclasses import dataclass, field
from statistics import mean

from app.domain.enums import Outcome, ProductCode
from app.domain.finance import MSP_RATE
from app.domain.products import PRODUCTS, Product, kassa_limit
from app.domain.scoring import ScoringResult


@dataclass(frozen=True)
class StopFactor:
    code: str
    title: str
    client_message: str


@dataclass(frozen=True)
class Enrichment:
    legal_status: str
    tax_arrears: bool
    account_blocked: bool
    bki_overdue_days: int
    bki_current_debt: int
    bki_inquiries_90d: int
    turnovers: list[int]
    business_age_months: int
    missing_fields: list[str] = field(default_factory=list)
    extra_turnover: int = 0
    issued_kassa: int = 0
    issued_debt: int = 0
    profile_changed: bool = False
    bki_unavailable: bool = False
    collateral_msp: bool = False
    tax_cured: bool = False


@dataclass(frozen=True)
class PolicyDecision:
    outcome: Outcome
    product: ProductCode
    rules: list[str]
    client_message: str
    specialist_summary: str
    offered_amount: int | None = None
    offered_term_months: int | None = None
    rate_annual: float | None = None
    limit_amount: int | None = None
    extra_fields: list[str] = field(default_factory=list)


def detect_stop_factors(enrichment: Enrichment) -> list[StopFactor]:
    found: list[StopFactor] = []
    if enrichment.legal_status != "active":
        found.append(
            StopFactor(
                "legal_status",
                "Статус в реестре",
                "Компания не действует по данным реестра.",
            )
        )
    if enrichment.account_blocked:
        found.append(
            StopFactor(
                "account_blocked",
                "Счёт",
                "Расчётный счёт ограничен. Сначала нужно снять ограничение.",
            )
        )
    if enrichment.tax_arrears:
        found.append(
            StopFactor(
                "tax_arrears",
                "Налоги",
                "Есть задолженность по налогам. Пока она не закрыта, кредит недоступен.",
            )
        )
    if enrichment.bki_overdue_days > 0:
        found.append(
            StopFactor(
                "bki_overdue",
                "Просрочка",
                "В кредитной истории есть действующая просрочка.",
            )
        )
    return found


def rate_from_score(key_rate: float, scoring: ScoringResult) -> float:
    if scoring.total >= 75:
        spread = 6.5
    elif scoring.total >= 60:
        spread = 9.0
    elif scoring.total >= 50:
        spread = 12.0
    else:
        spread = 16.0
    return round(key_rate + spread, 2)


def apply_policy(
    *,
    product_code: ProductCode,
    requested_amount: int,
    requested_term_months: int,
    enrichment: Enrichment,
    scoring: ScoringResult,
    key_rate: float,
) -> PolicyDecision:
    product: Product = PRODUCTS[product_code]
    avg = int(mean(enrichment.turnovers)) if enrichment.turnovers else 0
    rated_avg = avg + enrichment.extra_turnover
    raw_limit = kassa_limit(rated_avg) if product_code == ProductCode.KASSA else product.max_amount
    limit = max(0, raw_limit - enrichment.issued_kassa) if product_code == ProductCode.KASSA else raw_limit
    stops = detect_stop_factors(enrichment)
    if stops:
        messages = " ".join(s.client_message for s in stops)
        return PolicyDecision(
            outcome=Outcome.REJECT,
            product=product_code,
            rules=[f"stop:{s.code}" for s in stops],
            client_message=messages,
            specialist_summary="Автоотказ по стоп-факторам: " + ", ".join(s.title for s in stops),
            limit_amount=limit,
        )

    if enrichment.missing_fields:
        return PolicyDecision(
            outcome=Outcome.EXTRA_REQUEST,
            product=product_code,
            rules=["missing_fields"],
            client_message="Не хватает данных, чтобы закончить оценку. Дополните заявку — номер останется тем же.",
            specialist_summary="Автодозапрос: " + ", ".join(enrichment.missing_fields),
            extra_fields=list(enrichment.missing_fields),
            limit_amount=limit,
        )

    if enrichment.bki_unavailable:
        return PolicyDecision(
            outcome=Outcome.REVIEW,
            product=product_code,
            rules=["fallback:bki_timeout"],
            client_message="Бюро кредитных историй не ответило. Заявку посмотрит специалист вручную.",
            specialist_summary="Circuit breaker: таймаут БКИ. Нужна ручная верификация.",
            limit_amount=limit,
        )

    if enrichment.tax_cured and not enrichment.extra_turnover:
        return PolicyDecision(
            outcome=Outcome.REVIEW,
            product=product_code,
            rules=["cure:tax_cleared"],
            client_message="Налоговую задолженность закрыли. Теперь заявку смотрит специалист.",
            specialist_summary="Недоимка ФНС снята в моке. Нужно повторно оценить риск.",
            limit_amount=limit,
        )

    if enrichment.profile_changed:
        return PolicyDecision(
            outcome=Outcome.REVIEW,
            product=product_code,
            rules=["client:profile_changed"],
            client_message="Вы отметили, что данные устарели. Специалист сверит карточку и ответит.",
            specialist_summary="Клиент попросил ручную сверку реквизитов.",
            limit_amount=limit,
        )

    if enrichment.collateral_msp:
        return PolicyDecision(
            outcome=Outcome.REVIEW,
            product=product_code,
            rules=["collateral:msp"],
            client_message="Залог или поручительство МСП снижает риск. Специалист подтвердит ставку 18,5%.",
            specialist_summary="Клиент готов оформить поручительство Корпорации МСП. Рекомендуемая ставка 18,5%.",
            offered_amount=requested_amount,
            offered_term_months=max(product.min_term_months, min(product.max_term_months, requested_term_months)),
            rate_annual=MSP_RATE,
            limit_amount=limit,
        )

    if product_code == ProductCode.RAZVITIE:
        return PolicyDecision(
            outcome=Outcome.REVIEW,
            product=product_code,
            rules=["product:razvitie_requires_specialist"],
            client_message="Заявку на «Развитие» смотрит кредитный специалист. Обычно это один рабочий день.",
            specialist_summary="Продукт «Развитие» всегда уходит человеку. Скоринг — подсказка, не решение.",
            limit_amount=limit,
        )

    if scoring.total < 50:
        return PolicyDecision(
            outcome=Outcome.REVIEW,
            product=product_code,
            rules=["score:borderline"],
            client_message="По этой сумме решение примет специалист: хотим ещё раз посмотреть обороты и нагрузку.",
            specialist_summary=f"Пограничный скоринг {scoring.total}/100 при продукте «Касса».",
            limit_amount=limit,
        )

    term = max(product.min_term_months, min(product.max_term_months, requested_term_months))
    rate = rate_from_score(key_rate, scoring)

    if requested_amount <= limit:
        extra_rule = "kassa:other_bank_turnover" if enrichment.extra_turnover else "kassa:within_limit"
        return PolicyDecision(
            outcome=Outcome.OFFER,
            product=product_code,
            rules=[extra_rule, f"score:{scoring.band}"],
            client_message="Одобрили «Кассу» на запрошенных условиях. Лимит считается от оборотов.",
            specialist_summary="Автооферта: сумма внутри лимита, стоп-факторов нет, скоринг достаточный.",
            offered_amount=requested_amount,
            offered_term_months=term,
            rate_annual=rate,
            limit_amount=limit,
        )

    return PolicyDecision(
        outcome=Outcome.COUNTEROFFER,
        product=product_code,
        rules=["kassa:above_limit", f"score:{scoring.band}"],
        client_message=(
            f"По оборотам сейчас доступно {limit:,} ₽ вместо запрошенных {requested_amount:,} ₽."
        ).replace(",", " "),
        specialist_summary="Авто-встречка: запрос выше доступного лимита 50% оборота за вычетом выдач.",
        offered_amount=limit,
        offered_term_months=term,
        rate_annual=rate,
        limit_amount=limit,
    )
