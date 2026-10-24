from app.domain.enums import Actor, ApplicationStatus

TRANSITIONS: dict[ApplicationStatus, dict[str, ApplicationStatus]] = {
    ApplicationStatus.SUBMITTED: {
        "auto_offer": ApplicationStatus.OFFER,
        "auto_counteroffer": ApplicationStatus.COUNTEROFFER,
        "auto_reject": ApplicationStatus.REJECTED,
        "auto_review": ApplicationStatus.IN_REVIEW,
        "auto_extra": ApplicationStatus.EXTRA_REQUESTED,
    },
    ApplicationStatus.EXTRA_REQUESTED: {
        "client_extra": ApplicationStatus.SUBMITTED,
    },
    ApplicationStatus.IN_REVIEW: {
        "specialist_offer": ApplicationStatus.OFFER,
        "specialist_counteroffer": ApplicationStatus.COUNTEROFFER,
        "specialist_reject": ApplicationStatus.REJECTED,
        "specialist_extra": ApplicationStatus.EXTRA_REQUESTED,
    },
    ApplicationStatus.OFFER: {
        "client_accept": ApplicationStatus.SIGNING,
        "client_decline": ApplicationStatus.CLOSED,
    },
    ApplicationStatus.COUNTEROFFER: {
        "client_accept": ApplicationStatus.SIGNING,
        "client_decline": ApplicationStatus.CLOSED,
        "what_if": ApplicationStatus.SUBMITTED,
    },
    ApplicationStatus.SIGNING: {
        "client_sign": ApplicationStatus.ISSUED,
    },
    ApplicationStatus.REJECTED: {
        "cure_restart": ApplicationStatus.SUBMITTED,
    },
}

ACTION_ACTORS: dict[str, Actor] = {
    "submit": Actor.CLIENT,
    "auto_offer": Actor.SYSTEM,
    "auto_counteroffer": Actor.SYSTEM,
    "auto_reject": Actor.SYSTEM,
    "auto_review": Actor.SYSTEM,
    "auto_extra": Actor.SYSTEM,
    "client_extra": Actor.CLIENT,
    "client_accept": Actor.CLIENT,
    "client_decline": Actor.CLIENT,
    "client_sign": Actor.CLIENT,
    "specialist_offer": Actor.SPECIALIST,
    "specialist_counteroffer": Actor.SPECIALIST,
    "specialist_reject": Actor.SPECIALIST,
    "specialist_extra": Actor.SPECIALIST,
    "what_if": Actor.CLIENT,
    "cure_restart": Actor.CLIENT,
}

OUTCOME_TO_ACTION = {
    "offer": "auto_offer",
    "counteroffer": "auto_counteroffer",
    "reject": "auto_reject",
    "review": "auto_review",
    "extra_request": "auto_extra",
}


class IllegalTransitionError(ValueError):
    pass


def next_status(current: ApplicationStatus, action: str) -> ApplicationStatus:
    allowed = TRANSITIONS.get(current, {})
    if action not in allowed:
        raise IllegalTransitionError(f"Действие {action} недоступно в статусе {current}")
    return allowed[action]


def can(current: ApplicationStatus, action: str) -> bool:
    return action in TRANSITIONS.get(current, {})
