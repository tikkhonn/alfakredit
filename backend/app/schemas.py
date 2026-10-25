from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field

from app.domain.enums import ProductCode, PurposeCode


class LoginRequest(BaseModel):
    login: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class CompanyOut(BaseModel):
    id: str
    legal_form: str
    inn: str
    ogrn: str
    name: str
    short_name: str
    okved: str
    okved_name: str
    registered_at: date
    status: str
    director_name: str
    account_blocked: bool
    turnovers: list[int]
    avg_turnover: int
    kassa_limit: int
    kassa_ceiling: int
    issued_kassa: int
    business_age_months: int


class UserOut(BaseModel):
    id: str
    login: str
    full_name: str
    role: str
    company: CompanyOut | None


class RecommendRequest(BaseModel):
    purpose: PurposeCode
    amount: int | None = None
    term_months: int | None = None


class RecommendResponse(BaseModel):
    purpose: PurposeCode
    purpose_title: str
    purpose_subtitle: str
    why: str
    product: ProductCode
    product_name: str
    product_tagline: str
    suggested_amount: int
    suggested_term_months: int
    min_amount: int
    max_amount: int
    min_term_months: int
    max_term_months: int
    kassa_limit: int | None
    monthly_payment: int | None = None
    indicative_rate: float | None = None
    override_warning: str | None = None


class ApplicationCreate(BaseModel):
    purpose: PurposeCode
    product: ProductCode
    requested_amount: int = Field(gt=0)
    requested_term_months: int = Field(gt=0)
    purpose_details: str | None = None
    profile_changed: bool = False
    profile_note: str | None = None


class ExtraSubmit(BaseModel):
    purpose_details: str | None = None
    requested_amount: int | None = Field(default=None, gt=0)
    requested_term_months: int | None = Field(default=None, gt=0)


class SignRequest(BaseModel):
    code: str


class WhatIfRequest(BaseModel):
    action: str


class ChaosRequest(BaseModel):
    bki_down: bool


class QueueStats(BaseModel):
    queue_size: int
    auto_count: int
    manual_count: int
    auto_share: int | None = None


class SpecialistDecision(BaseModel):
    action: str
    amount: int | None = None
    term_months: int | None = None
    rate_annual: float | None = None
    extra_fields: list[str] = Field(default_factory=list)
    extra_comment: str | None = None
    reject_reason: str | None = None


class EventOut(BaseModel):
    id: str
    at: datetime
    actor: str
    action: str
    status: str
    message: str
    detail: dict[str, Any] | None = None


class ApplicationOut(BaseModel):
    id: str
    public_number: str
    purpose: str
    product: str
    requested_amount: int
    requested_term_months: int
    purpose_details: str | None
    status: str
    status_label: str
    client_message: str | None
    offer_amount: int | None
    offer_term_months: int | None
    offer_rate: float | None
    monthly_payment: int | None = None
    extra_fields: list[str]
    extra_comment: str | None
    decided_by: str | None
    profile_changed: bool = False
    profile_note: str | None = None
    extra_turnover: int = 0
    collateral_msp: bool = False
    created_at: datetime
    updated_at: datetime
    company: CompanyOut | None = None
    events: list[EventOut] = Field(default_factory=list)
    scoring: dict[str, Any] | None = None
    policy: dict[str, Any] | None = None
    enrichment: dict[str, Any] | None = None
    pipeline: list[dict[str, Any]] = Field(default_factory=list)
    available_actions: list[str] = Field(default_factory=list)
    dscr: float | None = None
    issued_monthly_payment: int = 0
    risk_memo: str | None = None
    schedule: list[dict[str, Any]] = Field(default_factory=list)
