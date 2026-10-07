"""Тексты уведомлений и их отправка.

Отправка идёт в фоне после ответа клиенту (BackgroundTasks): если Telegram тормозит
или недоступен, бронирование от этого не страдает.
"""

import logging
from datetime import datetime
from html import escape
from zoneinfo import ZoneInfo

from sqlalchemy import select, update
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.db.session import SessionLocal
from app.models import Booking, Equipment, User
from app.services.telegram import client
from app.services.telegram.client import TelegramError

log = logging.getLogger(__name__)

TZ = ZoneInfo(settings.timezone)
MONTHS = [
    "января",
    "февраля",
    "марта",
    "апреля",
    "мая",
    "июня",
    "июля",
    "августа",
    "сентября",
    "октября",
    "ноября",
    "декабря",
]


def fmt_dt(d: datetime) -> str:
    d = d.astimezone(TZ)
    return f"{d.day} {MONTHS[d.month - 1]}, {d:%H:%M}"


def fmt_period(start: datetime, end: datetime) -> str:
    s, e = start.astimezone(TZ), end.astimezone(TZ)
    if s.date() == e.date():
        return f"{fmt_dt(s)}–{e:%H:%M}"
    return f"{fmt_dt(s)} — {fmt_dt(e)}"


def fmt_rub(value) -> str:
    return f"{int(value):,}".replace(",", " ") + " ₽"


def plural(n: int, one: str, few: str, many: str) -> str:
    """1 час, 2 часа, 5 часов"""
    if n % 10 == 1 and n % 100 != 11:
        return one
    if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
        return few
    return many


def fmt_rate(b: Booking) -> str:
    n = b.quantity
    if b.rate_type == "hourly":
        return f"{n} {plural(n, 'час', 'часа', 'часов')}"
    return f"{n} {plural(n, 'смена', 'смены', 'смен')} по 8 ч"


def site_button(text: str, path: str) -> dict | None:
    """Кнопка-ссылка на сайт. Telegram не принимает адреса localhost — тогда без кнопки."""
    if "localhost" in settings.site_url or "127.0.0.1" in settings.site_url:
        return None
    return {"inline_keyboard": [[{"text": text, "url": settings.site_url.rstrip("/") + path}]]}


async def send(user: User, text: str, markup: dict | None = None) -> None:
    if not client.enabled() or user.telegram_chat_id is None:
        return
    params: dict = {"chat_id": user.telegram_chat_id, "text": text, "parse_mode": "HTML"}
    if markup:
        params["reply_markup"] = markup
    try:
        await client.call("sendMessage", params)
    except TelegramError as e:
        if e.status == 403:  # пользователь заблокировал бота — больше не пытаемся
            async with SessionLocal() as session:
                await session.execute(update(User).where(User.id == user.id).values(telegram_chat_id=None))
                await session.commit()
            log.info("Пользователь %s заблокировал бота, Telegram отвязан", user.id)
        else:
            log.warning("Не удалось отправить уведомление пользователю %s: %s", user.id, e)
    except Exception:
        log.exception("Не удалось отправить уведомление пользователю %s", user.id)


async def load(booking_id: int) -> Booking | None:
    async with SessionLocal() as session:
        return await session.scalar(
            select(Booking)
            .where(Booking.id == booking_id)
            .options(
                selectinload(Booking.user),
                selectinload(Booking.equipment).selectinload(Equipment.owner),
            )
        )


def header(b: Booking) -> str:
    operator = ", с оператором" if b.with_operator else ""
    return (
        f"<b>{escape(b.equipment.name)}</b>\n"
        f"{fmt_period(b.period.lower, b.period.upper)}\n"
        f"{fmt_rate(b)}{operator}, {fmt_rub(b.total_price)}"
    )


async def booking_event(booking_id: int, event: str) -> None:
    """Точка входа для фоновой задачи: event — что случилось с бронью."""
    b = await load(booking_id)
    if b is None:
        return
    owner, client_user = b.equipment.owner, b.user

    if event == "created":
        lines = [
            "🆕 <b>Новая заявка</b>",
            header(b),
            "",
            f"Клиент: {escape(client_user.full_name)}",
            f"Телефон: {escape(b.contact_phone)}",
        ]
        if b.delivery_address:
            lines.append(f"Адрес объекта: {escape(b.delivery_address)}")
        if b.comment:
            lines.append(f"Комментарий: {escape(b.comment)}")
        lines += [
            "",
            f"Позвоните клиенту и подтвердите бронь в разделе «Заявки». "
            f"Без подтверждения заявка отменится через {settings.booking_pending_ttl_hours} ч.",
        ]
        await send(owner, "\n".join(lines), site_button("Открыть заявки", "/my/requests"))

    elif event == "confirmed":
        phone = f", {escape(owner.phone)}" if owner.phone else ""
        text = f"✅ <b>Бронь подтверждена</b>\n{header(b)}\n\nВладелец: {escape(owner.full_name)}{phone}"
        await send(client_user, text, site_button("Мои брони", "/bookings"))

    elif event == "rejected":
        reason = f"\nПричина: {escape(b.reject_reason)}" if b.reject_reason else ""
        text = (
            f"❌ <b>Владелец отклонил заявку</b>\n{header(b)}{reason}\n\nПодберите другое время или технику в каталоге."
        )
        await send(client_user, text, site_button("Открыть каталог", "/catalog"))

    elif event == "cancelled":
        text = (
            f"↩️ <b>Клиент отменил бронь</b>\n{header(b)}\n\n"
            f"Клиент: {escape(client_user.full_name)}. Время снова свободно."
        )
        await send(owner, text)

    elif event == "expired":
        await send(
            client_user,
            f"⌛ <b>Заявка не подтверждена вовремя</b>\n{header(b)}\n\n"
            "Владелец не успел подтвердить её, время освободилось.",
            site_button("Открыть каталог", "/catalog"),
        )
        await send(
            owner,
            f"⌛ <b>Заявка сгорела без подтверждения</b>\n{header(b)}\n\nКлиент: {escape(client_user.full_name)}",
        )
