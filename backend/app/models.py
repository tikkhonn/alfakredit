from datetime import date, datetime, timezone
from typing import Any, Optional
from uuid import uuid4

from sqlalchemy import JSON, Column, UniqueConstraint
from sqlmodel import Field, Relationship, SQLModel


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def new_id() -> str:
    return str(uuid4())


class Company(SQLModel, table=True):
    id: str = Field(default_factory=new_id, primary_key=True)
    legal_form: str
    inn: str = Field(index=True, unique=True)
    ogrn: str
    name: str
    short_name: str
    okved: str
    okved_name: str
    registered_at: date
    status: str = "active"
    director_name: str
    account_blocked: bool = False
    turnovers: list[int] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    users: list["User"] = Relationship(back_populates="company")
    applications: list["Application"] = Relationship(back_populates="company")


class User(SQLModel, table=True):
    id: str = Field(default_factory=new_id, primary_key=True)
    login: str = Field(index=True, unique=True)
    password_hash: str
    full_name: str
    role: str
    company_id: str | None = Field(default=None, foreign_key="company.id")
    company: Optional[Company] = Relationship(back_populates="users")


class Application(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("public_number"),)

    id: str = Field(default_factory=new_id, primary_key=True)
    public_number: str = Field(index=True)
    company_id: str = Field(foreign_key="company.id", index=True)
    created_by_user_id: str = Field(foreign_key="user.id")
    purpose: str
    product: str
    requested_amount: int
    requested_term_months: int
    purpose_details: str | None = None
    status: str
    enrichment: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))
    scoring: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))
    policy: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))
    offer_amount: int | None = None
    offer_term_months: int | None = None
    offer_rate: float | None = None
    extra_fields: list[str] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    extra_comment: str | None = None
    client_message: str | None = None
    decided_by: str | None = None
    profile_changed: bool = False
    extra_turnover: int = 0
    collateral_msp: bool = False
    pipeline: list[dict[str, Any]] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)

    company: Optional[Company] = Relationship(back_populates="applications")
    events: list["ApplicationEvent"] = Relationship(back_populates="application")


class ApplicationEvent(SQLModel, table=True):
    id: str = Field(default_factory=new_id, primary_key=True)
    application_id: str = Field(foreign_key="application.id", index=True)
    at: datetime = Field(default_factory=utcnow)
    actor: str
    action: str
    status: str
    message: str
    detail: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))
    application: Optional[Application] = Relationship(back_populates="events")
