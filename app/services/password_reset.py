"""Восстановление пароля одноразовой ссылкой. В базе хранится только хэш кода"""

import contextlib
import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from app.core.config import settings
from app.models import User
from app.services import mailer
from app.services.telegram import client as telegram


def hash_code(code: str) -> str:
    return hashlib.sha256(code.encode()).hexdigest()


def issue_code(user: User) -> str:
    """Выпускает новый код (старый перестаёт действовать) и возвращает ссылку для сброса"""
    code = secrets.token_urlsafe(32)
    user.password_reset_hash = hash_code(code)
    user.password_reset_expires_at = datetime.now(UTC) + timedelta(minutes=settings.password_reset_ttl_minutes)
    return f"{settings.site_url.rstrip('/')}/reset-password?token={code}"


async def deliver(user: User, link: str) -> None:
    """Ссылку отправляем всеми доступными способами: на почту и в Telegram, если он привязан"""
    ttl = settings.password_reset_ttl_minutes
    text = (
        f"Здравствуйте, {user.full_name}!\n\n"
        f"Чтобы задать новый пароль на сайте «Ковш», откройте ссылку (действует {ttl} минут):\n{link}\n\n"
        "Если вы не запрашивали смену пароля, просто проигнорируйте это сообщение."
    )
    await mailer.send(user.email, "Восстановление пароля", text)
    if telegram.enabled() and user.telegram_chat_id:
        # Недоступный Telegram не должен ломать запрос сброса
        with contextlib.suppress(Exception):
            await telegram.call("sendMessage", {"chat_id": user.telegram_chat_id, "text": text})
