"""Заявки, которые владелец не подтвердил вовремя, сгорают и освобождают время."""

import asyncio
import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, or_, update

from app.core.config import settings
from app.db.session import SessionLocal
from app.models import Booking, BookingStatus

log = logging.getLogger(__name__)
CHECK_INTERVAL_SECONDS = 60


async def expire_stale_bookings() -> int:
    now = datetime.now(UTC)
    async with SessionLocal() as session:
        result = await session.execute(
            update(Booking)
            .where(
                Booking.status == BookingStatus.pending,
                or_(
                    Booking.created_at < now - timedelta(hours=settings.booking_pending_ttl_hours),
                    func.lower(Booking.period) <= now,  # время начала уже наступило
                ),
            )
            .values(status=BookingStatus.expired)
        )
        await session.commit()
        return result.rowcount or 0


async def expiry_loop() -> None:
    """Фоновая проверка раз в минуту. Подходит для одного процесса; если серверов станет
    несколько, задачу лучше перенести в планировщик (cron, Celery beat, APScheduler)."""
    while True:
        try:
            if count := await expire_stale_bookings():
                log.info("Сгорело неподтверждённых заявок: %s", count)
        except Exception:  # фоновая задача не должна умирать из-за разовой ошибки БД
            log.exception("Не удалось обработать просроченные заявки")
        await asyncio.sleep(CHECK_INTERVAL_SECONDS)
