"""Статистика владельца за месяц: заявки, выручка, загрузка техники по дням"""

from datetime import date, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import func, select

from app.api.deps import OwnerUser, SessionDep
from app.core.config import settings
from app.models import Booking, BookingStatus, Equipment
from app.schemas.equipment import Amount

router = APIRouter(tags=["stats"])

# Что считается состоявшейся или будущей арендой (в отличие от отказов и отмен)
DEALS = (BookingStatus.confirmed, BookingStatus.active, BookingStatus.completed)


class RequestCounts(BaseModel):
    total: int  # новые заявки за месяц
    pending: int
    confirmed: int  # подтверждены, в работе или завершены
    rejected: int
    cancelled: int
    expired: int


class EquipmentStats(BaseModel):
    id: int
    name: str
    busy_days: int  # дни, когда техника занята бронью с сайта или закрыта владельцем
    blocked_days: int  # из них закрыто владельцем (заказы не с сайта, ремонт)
    utilization: float  # доля занятых дней месяца, 0..1
    revenue: Amount
    deals: int


class DayLoad(BaseModel):
    day: date
    busy: int  # сколько единиц техники занято в этот день


class OwnerStats(BaseModel):
    month: str
    days_in_month: int
    equipment_count: int
    requests: RequestCounts
    revenue_completed: Amount  # завершённые аренды месяца
    revenue_expected: Amount  # подтверждённые и в работе — деньги, которые ещё придут
    utilization: float  # средняя загрузка всей техники
    equipment: list[EquipmentStats]
    days: list[DayLoad]


def month_bounds(month: str, tz: ZoneInfo) -> tuple[datetime, datetime, int]:
    try:
        year, mon = (int(x) for x in month.split("-"))
        start = datetime(year, mon, 1, tzinfo=tz)
    except ValueError as e:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Месяц в формате ГГГГ-ММ") from e
    end = datetime(year + mon // 12, mon % 12 + 1, 1, tzinfo=tz)
    return start, end, (end - start).days


@router.get("/owner/stats", response_model=OwnerStats)
async def owner_stats(
    session: SessionDep,
    user: OwnerUser,
    month: str | None = Query(default=None, pattern=r"^\d{4}-\d{2}$", description="ГГГГ-ММ, по умолчанию текущий"),
) -> OwnerStats:
    tz = ZoneInfo(settings.timezone)
    month = month or datetime.now(tz).strftime("%Y-%m")
    start, end, days_in_month = month_bounds(month, tz)

    equipment = list(
        await session.scalars(select(Equipment).where(Equipment.owner_id == user.id).order_by(Equipment.id))
    )
    ids = [e.id for e in equipment]

    # Заявки, созданные в этом месяце, по статусам (закрытия владельца — не заявки)
    counts = (
        dict(
            (
                await session.execute(
                    select(Booking.status, func.count())
                    .where(
                        Booking.equipment_id.in_(ids),
                        Booking.status != BookingStatus.blocked,
                        Booking.created_at >= start,
                        Booking.created_at < end,
                    )
                    .group_by(Booking.status)
                )
            ).all()
        )
        if ids
        else {}
    )

    # Всё, что занимает технику в этом месяце: сделки и закрытые владельцем дни
    occupying = (
        list(
            await session.scalars(
                select(Booking).where(
                    Booking.equipment_id.in_(ids),
                    Booking.status.in_((*DEALS, BookingStatus.blocked)),
                    Booking.period.op("&&")(func.tstzrange(start, end, "[)")),
                )
            )
        )
        if ids
        else []
    )

    def days_of(b: Booking) -> set[date]:
        """Календарные дни месяца (в часовом поясе сервиса), которые задевает бронь"""
        first = max(b.period.lower, start).astimezone(tz).date()
        last = (min(b.period.upper, end) - timedelta(microseconds=1)).astimezone(tz).date()
        return {first + timedelta(days=i) for i in range((last - first).days + 1)}

    busy: dict[int, set[date]] = {i: set() for i in ids}
    blocked: dict[int, set[date]] = {i: set() for i in ids}
    revenue: dict[int, Decimal] = dict.fromkeys(ids, Decimal(0))
    deals: dict[int, int] = dict.fromkeys(ids, 0)
    revenue_completed = revenue_expected = Decimal(0)

    for b in occupying:
        d = days_of(b)
        busy[b.equipment_id] |= d
        if b.status == BookingStatus.blocked:
            blocked[b.equipment_id] |= d
            continue
        # Выручку относим к месяцу начала аренды, чтобы длинная аренда не считалась дважды
        if start <= b.period.lower < end:
            revenue[b.equipment_id] += b.total_price
            deals[b.equipment_id] += 1
            if b.status == BookingStatus.completed:
                revenue_completed += b.total_price
            else:
                revenue_expected += b.total_price

    first_day = start.date()
    day_list = [first_day + timedelta(days=i) for i in range(days_in_month)]
    per_equipment = [
        EquipmentStats(
            id=e.id,
            name=e.name,
            busy_days=len(busy[e.id]),
            blocked_days=len(blocked[e.id]),
            utilization=round(len(busy[e.id]) / days_in_month, 3),
            revenue=revenue[e.id],
            deals=deals[e.id],
        )
        for e in equipment
    ]
    total = sum(counts.values())
    return OwnerStats(
        month=month,
        days_in_month=days_in_month,
        equipment_count=len(equipment),
        requests=RequestCounts(
            total=total,
            pending=counts.get(BookingStatus.pending, 0),
            confirmed=sum(counts.get(s, 0) for s in DEALS),
            rejected=counts.get(BookingStatus.rejected, 0),
            cancelled=counts.get(BookingStatus.cancelled, 0),
            expired=counts.get(BookingStatus.expired, 0),
        ),
        revenue_completed=revenue_completed,
        revenue_expected=revenue_expected,
        utilization=round(sum(s.utilization for s in per_equipment) / len(per_equipment), 3) if per_equipment else 0,
        equipment=per_equipment,
        days=[DayLoad(day=d, busy=sum(1 for i in ids if d in busy[i])) for d in day_list],
    )
