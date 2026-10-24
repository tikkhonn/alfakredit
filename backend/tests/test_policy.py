from app.domain.enums import Outcome, ProductCode
from app.domain.policy import Enrichment, apply_policy
from app.domain.products import kassa_limit
from app.domain.scoring import ScoringInput, score

CLEAN = Enrichment(
    legal_status="active",
    tax_arrears=False,
    account_blocked=False,
    bki_overdue_days=0,
    bki_current_debt=320_000,
    bki_inquiries_90d=1,
    turnovers=[2_400_000, 2_600_000, 2_500_000],
    business_age_months=90,
)


def _scoring(amount: int):
    return score(
        ScoringInput(
            business_age_months=CLEAN.business_age_months,
            turnovers=CLEAN.turnovers,
            requested_amount=amount,
            bki_overdue_days=0,
            bki_current_debt=320_000,
            bki_inquiries_90d=1,
        )
    )


def test_kassa_within_limit_is_auto_offer():
    amount = 800_000
    decision = apply_policy(
        product_code=ProductCode.KASSA,
        requested_amount=amount,
        requested_term_months=6,
        enrichment=CLEAN,
        scoring=_scoring(amount),
        key_rate=16.5,
    )
    assert decision.outcome == Outcome.OFFER
    assert decision.offered_amount == amount
    assert decision.rate_annual == 23.0


def test_kassa_above_limit_is_counteroffer():
    amount = 8_000_000
    limit = kassa_limit(2_500_000)
    decision = apply_policy(
        product_code=ProductCode.KASSA,
        requested_amount=amount,
        requested_term_months=6,
        enrichment=CLEAN,
        scoring=_scoring(amount),
        key_rate=16.5,
    )
    assert decision.outcome == Outcome.COUNTEROFFER
    assert decision.offered_amount == limit


def test_tax_arrears_is_hard_reject():
    dirty = Enrichment(**{**CLEAN.__dict__, "tax_arrears": True})
    decision = apply_policy(
        product_code=ProductCode.KASSA,
        requested_amount=500_000,
        requested_term_months=6,
        enrichment=dirty,
        scoring=_scoring(500_000),
        key_rate=16.5,
    )
    assert decision.outcome == Outcome.REJECT
    assert "stop:tax_arrears" in decision.rules


def test_razvitie_always_goes_to_specialist():
    decision = apply_policy(
        product_code=ProductCode.RAZVITIE,
        requested_amount=5_000_000,
        requested_term_months=24,
        enrichment=CLEAN,
        scoring=_scoring(5_000_000),
        key_rate=16.5,
    )
    assert decision.outcome == Outcome.REVIEW


def test_missing_fields_request_extra():
    missing = Enrichment(**{**CLEAN.__dict__, "missing_fields": ["purpose_details"]})
    decision = apply_policy(
        product_code=ProductCode.RAZVITIE,
        requested_amount=5_000_000,
        requested_term_months=24,
        enrichment=missing,
        scoring=_scoring(5_000_000),
        key_rate=16.5,
    )
    assert decision.outcome == Outcome.EXTRA_REQUEST
    assert decision.extra_fields == ["purpose_details"]
