from app.domain.finance import dscr, monthly_payment, round_amount


def test_round_amount_to_ten_thousand():
    assert round_amount(833_333) == 830_000
    assert round_amount(800_000) == 800_000


def test_annuity_near_audit_example():
    payment = monthly_payment(1_200_000, 23, 6)
    assert 210_000 <= payment <= 217_000


def test_dscr_bakery():
    value = dscr(2_500_000, "10.71", 213_500)
    assert value is not None
    assert value > 1
