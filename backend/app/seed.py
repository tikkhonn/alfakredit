from datetime import date

from sqlmodel import Session, select

from app.adapters.registry import BkiRecord, EgrulRecord, FnsRecord, MockRegistry
from app.domain.enums import LegalForm, ProductCode, PurposeCode
from app.models import Application, Company, User
from app.security import hash_password

IP_INN = "770712345678"
LLC_INN = "7708123456"

IP_TURNOVERS = [2_400_000, 2_450_000, 2_500_000, 2_550_000, 2_600_000, 2_500_000]
LLC_TURNOVERS = [1_800_000, 1_400_000, 1_100_000, 1_200_000, 1_000_000, 1_100_000]


def build_registry() -> MockRegistry:
    return MockRegistry(
        egrul={
            IP_INN: EgrulRecord(
                inn=IP_INN,
                ogrn="304770712345678",
                name="Индивидуальный предприниматель Волков Алексей Сергеевич",
                legal_form=LegalForm.IP,
                status="active",
                okved="10.71",
                okved_name="Производство хлеба и мучных кондитерских изделий",
                registered_at=date(2019, 3, 12),
                director_name="Волков Алексей Сергеевич",
            ),
            LLC_INN: EgrulRecord(
                inn=LLC_INN,
                ogrn="1027708123456",
                name='Общество с ограниченной ответственностью "ТехноСнаб"',
                legal_form=LegalForm.LLC,
                status="active",
                okved="41.20",
                okved_name="Строительство жилых и нежилых зданий",
                registered_at=date(2021, 8, 4),
                director_name="Соколова Ирина Павловна",
            ),
        },
        fns={
            IP_INN: FnsRecord(inn=IP_INN, tax_arrears=False, arrears_amount=0),
            LLC_INN: FnsRecord(inn=LLC_INN, tax_arrears=True, arrears_amount=486_000),
        },
        bki={
            IP_INN: BkiRecord(
                inn=IP_INN,
                overdue_days=0,
                current_debt=320_000,
                inquiries_90d=1,
                worst_status="ok",
                monthly_payment=18_000,
            ),
            LLC_INN: BkiRecord(
                inn=LLC_INN,
                overdue_days=0,
                current_debt=2_400_000,
                inquiries_90d=6,
                worst_status="ok",
                monthly_payment=95_000,
            ),
        },
    )


DEMO_ACCOUNTS = [
    {"login": "ip", "password": "ip123", "hint": "ИП Волков — чистый клиент, «Касса» решается сама"},
    {"login": "ooo", "password": "ooo123", "hint": "ООО ТехноСнаб — долг по налогам, можно смоделировать погашение"},
    {"login": "spec", "password": "spec123", "hint": "Кредитный специалист — очередь не пустая"},
]


def seed_if_empty(session: Session) -> None:
    existing = session.exec(select(User)).first()
    if existing:
        return

    bakery = Company(
        legal_form=LegalForm.IP.value,
        inn=IP_INN,
        ogrn="304770712345678",
        name="Индивидуальный предприниматель Волков Алексей Сергеевич",
        short_name="Пекарня «Восход»",
        okved="10.71",
        okved_name="Производство хлеба и мучных кондитерских изделий",
        registered_at=date(2019, 3, 12),
        status="active",
        director_name="Волков Алексей Сергеевич",
        account_blocked=False,
        turnovers=IP_TURNOVERS,
    )
    technosnab = Company(
        legal_form=LegalForm.LLC.value,
        inn=LLC_INN,
        ogrn="1027708123456",
        name='ООО "ТехноСнаб"',
        short_name="ТехноСнаб",
        okved="41.20",
        okved_name="Строительство жилых и нежилых зданий",
        registered_at=date(2021, 8, 4),
        status="active",
        director_name="Соколова Ирина Павловна",
        account_blocked=False,
        turnovers=LLC_TURNOVERS,
    )
    session.add(bakery)
    session.add(technosnab)
    session.flush()

    session.add(
        User(
            login="ip",
            password_hash=hash_password("ip123"),
            full_name="Волков Алексей Сергеевич",
            role="client",
            company_id=bakery.id,
        )
    )
    session.add(
        User(
            login="ooo",
            password_hash=hash_password("ooo123"),
            full_name="Соколова Ирина Павловна",
            role="client",
            company_id=technosnab.id,
        )
    )
    session.add(
        User(
            login="spec",
            password_hash=hash_password("spec123"),
            full_name="Морозова Дарья Андреевна",
            role="specialist",
        )
    )
    session.commit()


def ensure_demo_queue(session: Session) -> None:
    from app.services import OPEN_APPLICATION_STATUSES

    bakery = session.exec(select(Company).where(Company.inn == IP_INN)).first()
    if not bakery:
        return
    open_razvitie = session.exec(
        select(Application).where(
            Application.company_id == bakery.id,
            Application.product == ProductCode.RAZVITIE.value,
            Application.status.in_(list(OPEN_APPLICATION_STATUSES)),
        )
    ).first()
    if open_razvitie:
        return
    owner = session.exec(select(User).where(User.login == "ip")).first()
    if not owner:
        return
    from app.deps import get_registry
    from app.schemas import ApplicationCreate
    from app.services import create_application

    create_application(
        session,
        bakery,
        owner.id,
        ApplicationCreate(
            purpose=PurposeCode.GROWTH,
            product=ProductCode.RAZVITIE,
            requested_amount=4_500_000,
            requested_term_months=24,
            purpose_details="Вторая печь и ремонт точки на Таганке",
        ),
        get_registry(),
    )
