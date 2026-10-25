from __future__ import annotations

from dataclasses import dataclass, field
from statistics import mean, pstdev


@dataclass(frozen=True)
class FactorScore:
    code: str
    title: str
    points: int
    max_points: int
    comment: str


@dataclass(frozen=True)
class ScoringInput:
    business_age_months: int
    turnovers: list[int]
    requested_amount: int
    bki_overdue_days: int
    bki_current_debt: int
    bki_inquiries_90d: int
    issued_debt: int = 0
    bki_unavailable: bool = False


@dataclass(frozen=True)
class ScoringResult:
    total: int
    max_total: int
    factors: list[FactorScore] = field(default_factory=list)

    @property
    def band(self) -> str:
        if self.total >= 75:
            return "strong"
        if self.total >= 60:
            return "good"
        if self.total >= 50:
            return "moderate"
        return "weak"


def _age_factor(months: int) -> FactorScore:
    if months >= 36:
        points, comment = 20, "Бизнес старше трёх лет"
    elif months >= 24:
        points, comment = 16, "Бизнес работает больше двух лет"
    elif months >= 12:
        points, comment = 12, "Бизнес работает больше года"
    elif months >= 9:
        points, comment = 8, "Минимальный стаж для беззалогового оборота"
    else:
        points, comment = 4, "Короткий стаж повышает неопределённость"
    return FactorScore("age", "Срок бизнеса", points, 20, comment)


def _amount_factor(amount: int, issued_debt: int, avg_turnover: int) -> FactorScore:
    if avg_turnover <= 0:
        return FactorScore("amount", "Сумма к обороту", 0, 30, "Нет оборотов для оценки")
    ratio = (amount + issued_debt) / avg_turnover
    if issued_debt:
        load = f", уже выдано {issued_debt:,} ₽".replace(",", " ")
    else:
        load = ""
    if ratio <= 0.3:
        points, comment = 30, "Запрос заметно ниже среднемесячного оборота" + load
    elif ratio <= 0.5:
        points, comment = 22, "Запрос в пределах половины оборота" + load
    elif ratio <= 0.8:
        points, comment = 12, "Запрос сопоставим с оборотом" + load
    elif ratio <= 1.2:
        points, comment = 6, "Запрос превышает комфортную долю оборота" + load
    else:
        points, comment = 0, "Запрос существенно выше оборота" + load
    return FactorScore("amount", "Сумма к обороту", points, 30, comment)


def _stability_factor(turnovers: list[int]) -> FactorScore:
    if len(turnovers) < 2 or mean(turnovers) == 0:
        return FactorScore("stability", "Стабильность оборотов", 2, 20, "Недостаточно ряда оборотов")
    cv = pstdev(turnovers) / mean(turnovers)
    if cv < 0.1:
        points, comment = 20, "Обороты почти ровные"
    elif cv < 0.2:
        points, comment = 14, "Обороты умеренно колеблются"
    elif cv < 0.35:
        points, comment = 8, "Обороты заметно скачут"
    else:
        points, comment = 2, "Обороты нестабильны"
    return FactorScore("stability", "Стабильность оборотов", points, 20, comment)


def _bki_factor(
    overdue_days: int,
    current_debt: int,
    inquiries: int,
    avg_turnover: int,
    issued_debt: int,
    *,
    unavailable: bool = False,
) -> FactorScore:
    if unavailable:
        return FactorScore("bki", "Кредитная история", 0, 30, "Таймаут БКИ — требуется ручная проверка")
    if overdue_days > 0:
        return FactorScore("bki", "Кредитная история", 0, 30, "Есть действующая просрочка")
    points = 30
    comments: list[str] = []
    total_debt = current_debt + issued_debt
    if avg_turnover > 0 and total_debt > 2 * avg_turnover:
        points -= 14
        comments.append("высокая текущая долговая нагрузка")
    elif avg_turnover > 0 and total_debt > avg_turnover:
        points -= 8
        comments.append("заметная текущая задолженность")
    if issued_debt:
        comments.append("учтены выдачи в этом кабинете")
    if inquiries > 8:
        points -= 10
        comments.append("много запросов в БКИ за 90 дней")
    elif inquiries > 4:
        points -= 5
        comments.append("повышенное число запросов в БКИ")
    points = max(0, points)
    comment = "Чистое бюро, умеренная нагрузка" if not comments else "; ".join(comments)
    return FactorScore("bki", "Кредитная история", points, 30, comment)


def score(inp: ScoringInput) -> ScoringResult:
    avg = int(mean(inp.turnovers)) if inp.turnovers else 0
    factors = [
        _age_factor(inp.business_age_months),
        _amount_factor(inp.requested_amount, inp.issued_debt, avg),
        _stability_factor(inp.turnovers),
        _bki_factor(
            inp.bki_overdue_days,
            inp.bki_current_debt,
            inp.bki_inquiries_90d,
            avg,
            inp.issued_debt,
            unavailable=inp.bki_unavailable,
        ),
    ]
    total = sum(f.points for f in factors)
    return ScoringResult(total=total, max_total=100, factors=factors)
