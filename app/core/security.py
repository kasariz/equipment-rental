from datetime import UTC, datetime, timedelta

import jwt
from pwdlib import PasswordHash

from app.core.config import settings

ALGORITHM = "HS256"
ACCESS_TOKEN_COOKIE = "access_token"

password_hash = PasswordHash.recommended()  # Argon2

# Хэш-пустышка: проверяем пароль даже для несуществующего email,
# чтобы по времени ответа нельзя было узнать, зарегистрирован ли адрес
DUMMY_HASH = password_hash.hash("dummy-password-for-timing")


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    return password_hash.verify(password, hashed)


def password_stamp(password_changed_at: datetime | None) -> int:
    """Версия пароля в миллисекундах. Попадает в токен: после смены пароля старые токены не совпадут"""
    return int(password_changed_at.timestamp() * 1000) if password_changed_at else 0


def create_access_token(user_id: int, password_changed_at: datetime | None = None) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "pwd": password_stamp(password_changed_at),
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def decode_access_token(token: str) -> tuple[int, int] | None:
    """(id пользователя, версия пароля из токена) или None, если токен битый или просрочен."""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
        return int(payload["sub"]), int(payload.get("pwd", 0))
    except (jwt.PyJWTError, KeyError, ValueError):
        return None


def token_still_valid(stamp: int, password_changed_at: datetime | None) -> bool:
    """Токен действует, только если выпущен для текущей версии пароля.
    Сравнение точное, а не по времени: секундная точность времени выпуска пропустила бы
    токен, полученный в ту же секунду, когда меняли пароль"""
    return stamp == password_stamp(password_changed_at)
