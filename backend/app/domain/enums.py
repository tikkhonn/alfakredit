from enum import StrEnum


class LegalForm(StrEnum):
    IP = "ip"
    LLC = "llc"


class ProductCode(StrEnum):
    KASSA = "kassa"
    RAZVITIE = "razvitie"


class PurposeCode(StrEnum):
    CASH_GAP = "cash_gap"
    RESTOCK = "restock"
    GROWTH = "growth"


class ApplicationStatus(StrEnum):
    SUBMITTED = "submitted"
    EXTRA_REQUESTED = "extra_requested"
    IN_REVIEW = "in_review"
    OFFER = "offer"
    COUNTEROFFER = "counteroffer"
    REJECTED = "rejected"
    SIGNING = "signing"
    ISSUED = "issued"
    CLOSED = "closed"


class Actor(StrEnum):
    SYSTEM = "system"
    CLIENT = "client"
    SPECIALIST = "specialist"


class Outcome(StrEnum):
    OFFER = "offer"
    COUNTEROFFER = "counteroffer"
    EXTRA_REQUEST = "extra_request"
    REJECT = "reject"
    REVIEW = "review"


CLIENT_STATUS_LABELS: dict[ApplicationStatus, str] = {
    ApplicationStatus.SUBMITTED: "Приняли заявку",
    ApplicationStatus.EXTRA_REQUESTED: "Нужны уточнения",
    ApplicationStatus.IN_REVIEW: "Рассматриваем заявку",
    ApplicationStatus.OFFER: "Готово предложение",
    ApplicationStatus.COUNTEROFFER: "Можем одобрить на других условиях",
    ApplicationStatus.REJECTED: "Пока не одобрили",
    ApplicationStatus.SIGNING: "Подпишите документы",
    ApplicationStatus.ISSUED: "Деньги на счёте",
    ApplicationStatus.CLOSED: "Заявка закрыта",
}
