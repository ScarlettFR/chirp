import bcrypt


def _clip(raw: str) -> bytes:
    # bcrypt не жуёт больше 72 байт, обрезаем
    return raw.encode("utf-8")[:72]


def hash_pw(raw: str) -> str:
    return bcrypt.hashpw(_clip(raw), bcrypt.gensalt()).decode("utf-8")


def check_pw(raw: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(_clip(raw), hashed.encode("utf-8"))
    except ValueError:
        return False
