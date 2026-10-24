_chaos = {"bki_down": False}


def get_chaos() -> dict[str, bool]:
    return {"bki_down": bool(_chaos["bki_down"])}


def set_chaos(*, bki_down: bool) -> dict[str, bool]:
    _chaos["bki_down"] = bki_down
    return get_chaos()


def reset_chaos() -> None:
    _chaos["bki_down"] = False
