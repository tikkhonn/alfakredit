from __future__ import annotations

from dataclasses import asdict

from app.domain.enums import Outcome, ProductCode
from app.domain.policy import Enrichment, PolicyDecision, apply_policy
from app.domain.scoring import ScoringInput, ScoringResult, score
from app.domain.state_machine import OUTCOME_TO_ACTION


def decide(
    *,
    product_code: ProductCode,
    requested_amount: int,
    requested_term_months: int,
    enrichment: Enrichment,
    key_rate: float,
) -> tuple[ScoringResult, PolicyDecision, str]:
    scoring = score(
        ScoringInput(
            business_age_months=enrichment.business_age_months,
            turnovers=enrichment.turnovers,
            requested_amount=requested_amount,
            bki_overdue_days=enrichment.bki_overdue_days,
            bki_current_debt=enrichment.bki_current_debt,
            bki_inquiries_90d=enrichment.bki_inquiries_90d,
            issued_debt=enrichment.issued_debt,
        )
    )
    decision = apply_policy(
        product_code=product_code,
        requested_amount=requested_amount,
        requested_term_months=requested_term_months,
        enrichment=enrichment,
        scoring=scoring,
        key_rate=key_rate,
    )
    action = OUTCOME_TO_ACTION[decision.outcome.value]
    return scoring, decision, action


def scoring_to_dict(result: ScoringResult) -> dict:
    return {
        "total": result.total,
        "max_total": result.max_total,
        "band": result.band,
        "factors": [asdict(factor) for factor in result.factors],
    }


def policy_to_dict(decision: PolicyDecision) -> dict:
    payload = asdict(decision)
    payload["outcome"] = decision.outcome.value
    payload["product"] = decision.product.value
    return payload


OUTCOME_EVENT_COPY = {
    Outcome.OFFER: "Сформировали предложение",
    Outcome.COUNTEROFFER: "Предложили другие условия",
    Outcome.REJECT: "Заявку отклонили",
    Outcome.REVIEW: "Заявка у специалиста",
    Outcome.EXTRA_REQUEST: "Нужны уточнения по заявке",
}
