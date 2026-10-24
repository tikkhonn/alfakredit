from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from app.domain.enums import LegalForm


@dataclass(frozen=True)
class EgrulRecord:
    inn: str
    ogrn: str
    name: str
    legal_form: LegalForm
    status: str
    okved: str
    okved_name: str
    registered_at: date
    director_name: str


@dataclass(frozen=True)
class FnsRecord:
    inn: str
    tax_arrears: bool
    arrears_amount: int


@dataclass(frozen=True)
class BkiRecord:
    inn: str
    overdue_days: int
    current_debt: int
    inquiries_90d: int
    worst_status: str


class MockRegistry:
    """Локальные контракты ЕГРЮЛ / ФНС / БКИ на синтетике."""

    def __init__(
        self,
        egrul: dict[str, EgrulRecord],
        fns: dict[str, FnsRecord],
        bki: dict[str, BkiRecord],
    ) -> None:
        self._egrul = egrul
        self._fns = fns
        self._bki = bki

    def egrul(self, inn: str) -> EgrulRecord:
        record = self._egrul.get(inn)
        if not record:
            raise KeyError(f"ЕГРЮЛ: ИНН {inn} не найден")
        return record

    def fns(self, inn: str) -> FnsRecord:
        record = self._fns.get(inn)
        if not record:
            raise KeyError(f"ФНС: ИНН {inn} не найден")
        return record

    def bki(self, inn: str) -> BkiRecord:
        record = self._bki.get(inn)
        if not record:
            raise KeyError(f"БКИ: ИНН {inn} не найден")
        return record

    def cure_tax(self, inn: str) -> FnsRecord:
        record = self.fns(inn)
        cleared = FnsRecord(inn=record.inn, tax_arrears=False, arrears_amount=0)
        self._fns[inn] = cleared
        return cleared
