from app.domain.scoring import ScoringInput, score


def test_clean_ip_scores_high():
    result = score(
        ScoringInput(
            business_age_months=90,
            turnovers=[2_400_000, 2_600_000, 2_500_000],
            requested_amount=800_000,
            bki_overdue_days=0,
            bki_current_debt=320_000,
            bki_inquiries_90d=1,
        )
    )
    assert result.total >= 75
    assert result.band == "strong"


def test_overdue_zeroes_bki_factor():
    result = score(
        ScoringInput(
            business_age_months=40,
            turnovers=[1_000_000, 1_000_000, 1_000_000],
            requested_amount=300_000,
            bki_overdue_days=15,
            bki_current_debt=0,
            bki_inquiries_90d=0,
        )
    )
    bki = next(factor for factor in result.factors if factor.code == "bki")
    assert bki.points == 0
