"""Минимальный клиент Telegram Bot API: нам нужны всего четыре метода, библиотека не нужна."""

from typing import Any

import httpx

from app.core.config import settings


class TelegramError(Exception):
    def __init__(self, status: int, description: str):
        super().__init__(f"Telegram {status}: {description}")
        self.status = status
        self.description = description


def enabled() -> bool:
    return bool(settings.telegram_bot_token)


async def call(method: str, params: dict[str, Any] | None = None, *, timeout: float = 10) -> Any:
    url = f"{settings.telegram_api_base}/bot{settings.telegram_bot_token}/{method}"
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(url, json=params or {})
    data = response.json()
    if not data.get("ok"):
        raise TelegramError(data.get("error_code", response.status_code), data.get("description", ""))
    return data["result"]
