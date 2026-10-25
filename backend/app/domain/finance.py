from __future__ import annotations

OKVED_MARGIN: dict[str, float] = {
    "10.71": 0.12,
    "41.20": 0.08,
}

DEFAULT_MARGIN = 0.1
MSP_RATE = 18.5
AMOUNT_STEP = 10_000


def round_amount(value: int, step: int = AMOUNT_STEP) -> int:
    if value <= 0:
        return step
    return max(step, int(round(value / step) * step))


def monthly_payment(principal: int, rate_annual: float, months: int) -> int:
    if principal <= 0 or months <= 0:
        return 0
    rate = rate_annual / 100 / 12
    if rate <= 0:
        return principal // months
    factor = (1 + rate) ** months
    return int(round(principal * rate * factor / (factor - 1)))


def payment_schedule(principal: int, rate_annual: float, months: int) -> list[dict[str, int | float]]:
    payment = monthly_payment(principal, rate_annual, months)
    if payment <= 0:
        return []
    rate = rate_annual / 100 / 12
    remaining = float(principal)
    rows: list[dict[str, int | float]] = []
    for month in range(1, months + 1):
        interest = remaining * rate
        principal_part = payment - interest
        if month == months:
            principal_part = remaining
            payment_this = int(round(principal_part + interest))
        else:
            payment_this = payment
        remaining = max(0.0, remaining - principal_part)
        rows.append(
            {
                "month": month,
                "payment": payment_this,
                "principal": int(round(principal_part)),
                "interest": int(round(interest)),
                "remaining": int(round(remaining)),
            }
        )
    return rows


def estimated_monthly_profit(avg_turnover: int, okved: str) -> int:
    margin = OKVED_MARGIN.get(okved, DEFAULT_MARGIN)
    return int(round(avg_turnover * margin))


def dscr(avg_turnover: int, okved: str, payment: int, other_debt_payment: int = 0) -> float | None:
    total_payment = payment + max(0, other_debt_payment)
    if total_payment <= 0:
        return None
    return round(estimated_monthly_profit(avg_turnover, okved) / total_payment, 2)


def extra_turnover_for_request(avg_turnover: int, issued: int, requested: int, share: float = 0.5) -> int:
    target_base = int((requested + issued) / share)
    return max(0, target_base - avg_turnover)
