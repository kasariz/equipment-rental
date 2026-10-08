"""Оповещения администратору в Telegram: ошибки на сервере и перезапуски.

Используется отдельный бот (ALERT_BOT_TOKEN), не бот заявок: алерты не смешиваются
с уведомлениями пользователей и приходят, даже если с основным ботом что-то случилось.
Одинаковые ошибки присылаются не чаще раза в 10 минут, чтобы при сбое не завалить чат.
"""

import asyncio
import logging
import time
import traceback

import httpx

from app.core.config import settings

THROTTLE_SECONDS = 600
MAX_LENGTH = 3500  # у Telegram предел 4096 символов, оставляем запас

_last_sent: dict[str, float] = {}
_tasks: set[asyncio.Task] = set()  # держим ссылки, чтобы задачи не собрал сборщик мусора


def enabled() -> bool:
    return bool(settings.alert_bot_token and settings.alert_chat_id)


def should_send(key: str) -> bool:
    now = time.monotonic()
    if now - _last_sent.get(key, -THROTTLE_SECONDS) < THROTTLE_SECONDS:
        return False
    _last_sent[key] = now
    return True


async def send_alert(text: str, key: str | None = None) -> bool:
    """Никогда не бросает исключений: сбой мониторинга не должен ломать сайт"""
    if not enabled() or not should_send(key or text):
        return False
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                f"{settings.telegram_api_base}/bot{settings.alert_bot_token}/sendMessage",
                json={"chat_id": settings.alert_chat_id, "text": text[:MAX_LENGTH]},
            )
        return response.status_code == 200
    except Exception:
        return False


class TelegramAlertHandler(logging.Handler):
    """Все записи уровня ERROR из логов уходят администратору в Telegram"""

    def __init__(self) -> None:
        super().__init__(level=logging.ERROR)

    def emit(self, record: logging.LogRecord) -> None:
        if record.name.startswith("httpx"):
            return  # ошибки отправки самого алерта не пересылаем — иначе зациклимся
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return
        summary = record.getMessage()
        details = ""
        if record.exc_info and record.exc_info[1] is not None:
            exc = record.exc_info[1]
            summary = f"{summary}\n{type(exc).__name__}: {exc}"
            details = "".join(traceback.format_exception(*record.exc_info)[-3:])
        text = f"🔴 Ошибка на сервере «Ковш»\n\n{summary}\n\n{details}".strip()
        # Ключ для антиспама — тип ошибки и место, а не весь текст: так повторы одной ошибки склеиваются
        key = f"{record.name}:{record.pathname}:{record.lineno}:{summary[:200]}"
        task = loop.create_task(send_alert(text, key=key))
        _tasks.add(task)
        task.add_done_callback(_tasks.discard)


def install() -> None:
    if enabled() and not any(isinstance(h, TelegramAlertHandler) for h in logging.getLogger().handlers):
        logging.getLogger().addHandler(TelegramAlertHandler())
