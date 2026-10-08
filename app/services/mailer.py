"""Отправка писем через SMTP (например, ящик на Яндекс 360 или Mail.ru с паролем приложения)"""

import asyncio
import logging
import smtplib
from email.message import EmailMessage

from app.core.config import settings

log = logging.getLogger(__name__)


def enabled() -> bool:
    return bool(settings.smtp_host and settings.smtp_from)


def _send(to: str, subject: str, text: str) -> None:
    msg = EmailMessage()
    msg["From"], msg["To"], msg["Subject"] = settings.smtp_from, to, subject
    msg.set_content(text)
    with smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, timeout=15) as smtp:
        if settings.smtp_user:
            smtp.login(settings.smtp_user, settings.smtp_password)
        smtp.send_message(msg)


async def send(to: str, subject: str, text: str) -> bool:
    """smtplib синхронный — отправляем в отдельном потоке, чтобы не блокировать сервер"""
    if not enabled():
        return False
    try:
        await asyncio.to_thread(_send, to, subject, text)
        return True
    except Exception:
        log.exception("Не удалось отправить письмо на %s", to)
        return False
