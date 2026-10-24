from dataclasses import dataclass

from app.domain.enums import ProductCode, PurposeCode
from app.domain.finance import AMOUNT_STEP


@dataclass(frozen=True)
class Product:
    code: ProductCode
    name: str
    tagline: str
    kind: str
    min_amount: int
    max_amount: int
    min_term_months: int
    max_term_months: int
    auto_route: bool
    limit_share_of_turnover: float | None


PRODUCTS: dict[ProductCode, Product] = {
    ProductCode.KASSA: Product(
        code=ProductCode.KASSA,
        name="Касса",
        tagline="Оборотный экспресс-кредит под поступления на счёт, без залога",
        kind="express_working_capital",
        min_amount=300_000,
        max_amount=15_000_000,
        min_term_months=1,
        max_term_months=12,
        auto_route=True,
        limit_share_of_turnover=0.5,
    ),
    ProductCode.RAZVITIE: Product(
        code=ProductCode.RAZVITIE,
        name="Развитие",
        tagline="Срочный кредит на рост и оборудование — решение специалиста",
        kind="term_loan",
        min_amount=1_000_000,
        max_amount=30_000_000,
        min_term_months=12,
        max_term_months=36,
        auto_route=False,
        limit_share_of_turnover=None,
    ),
}

PURPOSE_TO_PRODUCT: dict[PurposeCode, ProductCode] = {
    PurposeCode.CASH_GAP: ProductCode.KASSA,
    PurposeCode.RESTOCK: ProductCode.KASSA,
    PurposeCode.GROWTH: ProductCode.RAZVITIE,
}

PURPOSE_COPY: dict[PurposeCode, dict[str, str]] = {
    PurposeCode.CASH_GAP: {
        "title": "Кассовый разрыв",
        "subtitle": "Счёт уже выставили, оплата от покупателей придёт позже",
        "why": "«Касса» — оборотный экспресс-кредит. Лимит считается от ваших поступлений, залог не нужен.",
    },
    PurposeCode.RESTOCK: {
        "title": "Закупка и оборот",
        "subtitle": "Товар, сырьё или сезон — короткий цикл",
        "why": "Короткий лимит «Кассы» закрывает закупку, если сумма сопоставима с оборотом.",
    },
    PurposeCode.GROWTH: {
        "title": "Рост и оборудование",
        "subtitle": "Станки, ремонт, новая точка, долгий проект",
        "why": "Это уже не кассовый разрыв. Заявку на «Развитие» смотрит кредитный специалист.",
    },
}


def recommend_product(purpose: PurposeCode) -> Product:
    return PRODUCTS[PURPOSE_TO_PRODUCT[purpose]]


def kassa_limit(avg_turnover: int) -> int:
    product = PRODUCTS[ProductCode.KASSA]
    raw = int(avg_turnover * (product.limit_share_of_turnover or 0.5))
    capped = max(product.min_amount, min(product.max_amount, raw))
    return (capped // AMOUNT_STEP) * AMOUNT_STEP
