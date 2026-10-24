from typing import Annotated

from fastapi import APIRouter, Depends

from app.demo_state import get_chaos, set_chaos
from app.deps import get_current_user
from app.models import User
from app.schemas import ChaosRequest

router = APIRouter(tags=["demo"])


@router.get("/demo/chaos")
def read_chaos(_: Annotated[User, Depends(get_current_user)]) -> dict[str, bool]:
    return get_chaos()


@router.post("/demo/chaos")
def write_chaos(
    payload: ChaosRequest,
    _: Annotated[User, Depends(get_current_user)],
) -> dict[str, bool]:
    return set_chaos(bki_down=payload.bki_down)
