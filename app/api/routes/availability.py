"""Календарь владельца: закрытие времени, когда техника занята вне сайта или на ремонте.

Закрытие хранится в таблице броней со статусом blocked. Так его защищает то же ограничение
bookings_no_overlap: закрыть время поверх брони или забронировать закрытое время нельзя
даже при одновременных запросах.
"""

from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import Range
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from app.api.deps import OwnerUser, SessionDep
from app.api.routes.bookings import BLOCKING, is_exclusion_violation
from app.api.routes.equipment import get_managed_equipment
from app.models import Booking, BookingStatus, RateType

router = APIRouter(tags=["availability"])


class BlockCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    start: datetime
    end: datetime
    reason: str | None = Field(default=None, max_length=200, description="Например: «заказ по телефону», «ТО»")

    @model_validator(mode="after")
    def check_period(self) -> "BlockCreate":
        if self.start.tzinfo is None or self.end.tzinfo is None:
            raise ValueError("Даты должны быть с часовым поясом")
        if self.end <= self.start:
            raise ValueError("Конец периода должен быть позже начала")
        if self.end - self.start > timedelta(days=366):
            raise ValueError("Закрыть можно не больше года за раз")
        return self


class CalendarItem(BaseModel):
    id: int
    kind: str  # booking — бронь клиента, block — время закрыто владельцем
    start: datetime
    end: datetime
    status: BookingStatus
    reason: str | None = None
    client_name: str | None = None


@router.get("/equipment/{equipment_id}/calendar", response_model=list[CalendarItem])
async def equipment_calendar(
    equipment_id: int,
    session: SessionDep,
    user: OwnerUser,
    date_from: datetime = Query(alias="from"),
    date_to: datetime = Query(alias="to"),
) -> list[CalendarItem]:
    """Для владельца: брони и закрытое время с подробностями. Публично доступна только занятость"""
    await get_managed_equipment(session, equipment_id, user)
    rows = await session.scalars(
        select(Booking)
        .where(
            Booking.equipment_id == equipment_id,
            Booking.status.in_(BLOCKING),
            Booking.period.op("&&")(Range(date_from, date_to, bounds="[)")),
        )
        .options(selectinload(Booking.user))
        .order_by(func.lower(Booking.period))
    )
    return [
        CalendarItem(
            id=b.id,
            kind="block" if b.status == BookingStatus.blocked else "booking",
            start=b.period.lower,
            end=b.period.upper,
            status=b.status,
            reason=b.comment if b.status == BookingStatus.blocked else None,
            client_name=None if b.status == BookingStatus.blocked else b.user.full_name,
        )
        for b in rows
    ]


@router.post("/equipment/{equipment_id}/blocks", response_model=CalendarItem, status_code=status.HTTP_201_CREATED)
async def create_block(equipment_id: int, data: BlockCreate, session: SessionDep, user: OwnerUser) -> CalendarItem:
    eq = await get_managed_equipment(session, equipment_id, user)
    block = Booking(
        user_id=eq.owner_id,
        equipment_id=eq.id,
        period=Range(data.start, data.end, bounds="[)"),
        rate_type=RateType.shift.value,
        quantity=1,
        contact_phone="",
        comment=data.reason or None,
        rental_price=0,
        total_price=0,
        status=BookingStatus.blocked,
    )
    session.add(block)
    try:
        await session.commit()
    except IntegrityError as e:
        await session.rollback()
        if is_exclusion_violation(e):
            raise HTTPException(
                status.HTTP_409_CONFLICT, detail="На эти дни уже есть бронь или закрытие. Выберите другие даты"
            ) from None
        raise
    return CalendarItem(
        id=block.id, kind="block", start=data.start, end=data.end, status=block.status, reason=block.comment
    )


@router.delete("/equipment/{equipment_id}/blocks/{block_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_block(equipment_id: int, block_id: int, session: SessionDep, user: OwnerUser) -> None:
    await get_managed_equipment(session, equipment_id, user)
    block = await session.get(Booking, block_id)
    if block is None or block.equipment_id != equipment_id or block.status != BookingStatus.blocked:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Закрытие не найдено")
    await session.delete(block)
    await session.commit()
