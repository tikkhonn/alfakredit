import pytest

from app.domain.enums import ApplicationStatus
from app.domain.state_machine import IllegalTransitionError, next_status


def test_happy_path_transitions():
    status = ApplicationStatus.SUBMITTED
    status = next_status(status, "auto_offer")
    status = next_status(status, "client_accept")
    status = next_status(status, "client_sign")
    assert status == ApplicationStatus.ISSUED


def test_illegal_sign_from_review():
    with pytest.raises(IllegalTransitionError):
        next_status(ApplicationStatus.IN_REVIEW, "client_sign")


def test_what_if_and_cure_restart():
    assert next_status(ApplicationStatus.COUNTEROFFER, "what_if") == ApplicationStatus.SUBMITTED
    assert next_status(ApplicationStatus.REJECTED, "cure_restart") == ApplicationStatus.SUBMITTED
