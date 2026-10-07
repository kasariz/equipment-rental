"""Бот, который привязывает Telegram к аккаунту на сайте.

Работает через long polling (getUpdates): для разработки не нужен публичный адрес.
На продакшене это можно заменить вебхуком, логика обработки останется той же.
"""

import asyncio
import logging
from datetime import UTC, datetime

import httpx
from sqlalchemy import select, update

from app.db.session import SessionLocal
from app.models import User
from app.services.telegram import client
from app.services.telegram.client import TelegramError

log = logging.getLogger(__name__)

_username: str | None = None  # @username бота, нужен для ссылки t.me/<username>

HELP = (
    "Это бот сервиса аренды спецтехники «Ковш». Он присылает уведомления о заявках.\n\n"
    "Чтобы подключить уведомления, откройте профиль на сайте и нажмите «Подключить Telegram».\n"
    "Отключить: /stop"
)


async def bot_username() -> str:
    global _username
    if _username is None:
        _username = (await client.call("getMe"))["username"]
    return _username


async def reply(chat_id: int, text: str) -> None:
    try:
        await client.call("sendMessage", {"chat_id": chat_id, "text": text})
    except TelegramError as e:  # например, пользователь успел заблокировать бота
        log.warning("Бот не смог ответить в чат %s: %s", chat_id, e)


async def link_account(chat_id: int, code: str) -> None:
    async with SessionLocal() as session:
        user = await session.scalar(select(User).where(User.telegram_link_code == code))
        if user is None or user.telegram_link_expires_at is None or user.telegram_link_expires_at < datetime.now(UTC):
            await reply(chat_id, "Ссылка устарела. Нажмите «Подключить Telegram» в профиле на сайте ещё раз.")
            return
        # Один чат — один аккаунт: если этот Telegram был привязан к другому аккаунту, отвязываем
        await session.execute(
            update(User).where(User.telegram_chat_id == chat_id, User.id != user.id).values(telegram_chat_id=None)
        )
        user.telegram_chat_id = chat_id
        user.telegram_link_code = None
        user.telegram_link_expires_at = None
        await session.commit()
        name = user.full_name
    await reply(chat_id, f"Готово, {name}! Уведомления о заявках будут приходить сюда.\nОтключить: /stop")


async def unlink_chat(chat_id: int) -> None:
    async with SessionLocal() as session:
        result = await session.execute(
            update(User).where(User.telegram_chat_id == chat_id).values(telegram_chat_id=None)
        )
        await session.commit()
    if result.rowcount:
        await reply(chat_id, "Уведомления отключены. Подключить снова можно в профиле на сайте.")
    else:
        await reply(chat_id, "Этот чат не был привязан к аккаунту.")


async def handle_update(upd: dict) -> None:
    message = upd.get("message") or {}
    text: str = message.get("text") or ""
    chat_id = (message.get("chat") or {}).get("id")
    if chat_id is None or (message.get("chat") or {}).get("type") != "private":
        return  # группы и каналы игнорируем: уведомления содержат телефоны клиентов
    if text.startswith("/start"):
        parts = text.split(maxsplit=1)
        if len(parts) == 2:
            await link_account(chat_id, parts[1].strip())
        else:
            await reply(chat_id, HELP)
    elif text.startswith("/stop"):
        await unlink_chat(chat_id)
    else:
        await reply(chat_id, HELP)


async def polling_loop() -> None:
    if not client.enabled():
        log.info("TELEGRAM_BOT_TOKEN не задан: Telegram-уведомления выключены")
        return
    offset: int | None = None
    while True:
        try:
            await bot_username()
            updates = await client.call(
                "getUpdates",
                {"offset": offset, "timeout": 25, "allowed_updates": ["message"]},
                timeout=35,
            )
            for upd in updates:
                offset = upd["update_id"] + 1
                try:
                    await handle_update(upd)
                except Exception:
                    log.exception("Не удалось обработать сообщение боту")
        except asyncio.CancelledError:
            raise
        except httpx.TimeoutException:
            continue
        except TelegramError as e:
            if e.status == 409:
                log.warning("Этого бота уже опрашивает другой процесс: %s", e.description)
            elif e.status == 401:
                log.error("Неверный TELEGRAM_BOT_TOKEN, уведомления выключены")
                return
            else:
                log.warning("Ошибка Telegram: %s", e)
            await asyncio.sleep(10)
        except Exception:
            log.exception("Ошибка при опросе Telegram")
            await asyncio.sleep(5)
