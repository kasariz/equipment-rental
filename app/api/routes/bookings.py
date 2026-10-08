from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, status
from sqlalchemy import exists, func, select
from sqlalchemy.dialects.postgresql import Range
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUser, OwnerUser, SessionDep
from app.api.routes.geo import ensure_normalized
from app.core.config import settings
from app.models import Booking, BookingStatus, Equipment, EquipmentStatus, ReviewDirection, User, UserRole
from app.schemas.booking import (
    BookingCreate,
    BookingEquipment,
    BookingParams,
    BookingRead,
    BusyInterval,
    Contact,
    QuoteRead,
    RejectBody,
)
from app.services.pricing import PricingError, Quote, calculate
from app.services.ratings import user_ratings
from app.services.telegram.notifications import booking_event

router = APIRouter(tags=["bookings"])

# Брони, которые занимают технику. Совпадает с условием ограничения bookings_no_overlap
BLOCKING = (BookingStatus.pending, BookingStatus.confirmed, BookingStatus.active, BookingStatus.blocked)
# Когда клиенту можно показать телефон владельца
OWNER_CONTACT_VISIBLE = (BookingStatus.confirmed, BookingStatus.active, BookingStatus.completed)


# ---------- вспомогательное ----------


def unprocessable(detail: str) -> HTTPException:
    return HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, detail=detail)


def is_exclusion_violation(error: IntegrityError) -> bool:
    """SQLSTATE 23P01: сработало ограничение EXCLUDE, то есть время уже занято."""
    orig = error.orig
    code = getattr(orig, "sqlstate", None) or getattr(orig.__cause__, "sqlstate", None)
    return code == "23P01"


async def quote_for(session: AsyncSession, params: BookingParams) -> tuple[Equipment, Quote]:
    eq = await session.get(Equipment, params.equipment_id)
    if eq is None or eq.status != EquipmentStatus.available:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Эта техника сейчас не сдаётся")

    now = datetime.now(UTC)
    if params.start < now + timedelta(hours=settings.booking_min_lead_hours):
        raise unprocessable(
            f"Заявку можно оставить не позднее чем за {settings.booking_min_lead_hours} ч до начала: "
            "владельцу нужно время, чтобы позвонить"
        )
    if params.start > now + timedelta(days=settings.booking_max_days_ahead):
        raise unprocessable(f"Бронировать можно не дальше чем на {settings.booking_max_days_ahead} дней вперёд")

    try:
        quote = calculate(eq, params.rate_type, params.start, params.quantity)
    except PricingError as e:
        raise unprocessable(str(e)) from e
    return eq, quote


async def is_free(session: AsyncSession, equipment_id: int, start: datetime, end: datetime) -> bool:
    busy = await session.scalar(
        select(
            exists().where(
                Booking.equipment_id == equipment_id,
                Booking.status.in_(BLOCKING),
                Booking.period.op("&&")(Range(start, end, bounds="[)")),
            )
        )
    )
    return not busy


def booking_options():
    return (
        selectinload(Booking.equipment).selectinload(Equipment.photos),
        selectinload(Booking.equipment).selectinload(Equipment.category),
        selectinload(Booking.equipment).selectinload(Equipment.owner),
        selectinload(Booking.user),
        selectinload(Booking.reviews),
    )


async def with_renter_ratings(session: AsyncSession, items: list[BookingRead]) -> list[BookingRead]:
    ratings = await user_ratings(
        session, [i.client.id for i in items if i.client and i.client.id], ReviewDirection.about_renter
    )
    for item in items:
        if item.client and item.client.id in ratings:
            item.client.rating, item.client.reviews_count = ratings[item.client.id]
    return items


def to_read(b: Booking, *, for_owner: bool) -> BookingRead:
    eq = b.equipment
    owner = None
    if not for_owner and b.status in OWNER_CONTACT_VISIBLE:
        owner = Contact(full_name=eq.owner.full_name, phone=eq.owner.phone)
    return BookingRead(
        id=b.id,
        status=b.status,
        rate_type=b.rate_type,
        quantity=b.quantity,
        start=b.period.lower,
        end=b.period.upper,
        delivery_address=b.delivery_address,
        comment=b.comment,
        contact_phone=b.contact_phone,
        reject_reason=b.reject_reason,
        total_price=b.total_price,
        created_at=b.created_at,
        reviewed=any(r.direction == ReviewDirection.about_owner for r in b.reviews),
        renter_reviewed=any(r.direction == ReviewDirection.about_renter for r in b.reviews),
        equipment=BookingEquipment(
            id=eq.id,
            name=eq.name,
            category=eq.category.name,
            address=eq.address,
            cover_url=eq.photos[0].url if eq.photos else None,
        ),
        client=Contact(id=b.user_id, full_name=b.user.full_name, phone=b.contact_phone) if for_owner else None,
        owner=owner,
    )


async def load_booking(session: AsyncSession, booking_id: int) -> Booking:
    # FOR UPDATE: если владелец нажмёт «Подтвердить», а клиент в ту же секунду «Отменить»,
    # второй запрос дождётся первого и увидит уже новый статус
    booking = await session.scalar(
        select(Booking)
        .where(Booking.id == booking_id)
        .options(*booking_options())
        .with_for_update(of=Booking)
        .execution_options(populate_existing=True)
    )
    if booking is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Заявка не найдена")
    return booking


async def reload(session: AsyncSession, booking_id: int) -> Booking:
    booking = await session.scalar(
        select(Booking)
        .where(Booking.id == booking_id)
        .options(*booking_options())
        .execution_options(populate_existing=True)
    )
    assert booking is not None
    return booking


# Допустимые переходы статусов: действие → (из каких статусов, в какой)
TRANSITIONS: dict[str, tuple[tuple[BookingStatus, ...], BookingStatus]] = {
    "cancel": ((BookingStatus.pending, BookingStatus.confirmed), BookingStatus.cancelled),
    "confirm": ((BookingStatus.pending,), BookingStatus.confirmed),
    "reject": ((BookingStatus.pending, BookingStatus.confirmed), BookingStatus.rejected),
    "start": ((BookingStatus.confirmed,), BookingStatus.active),
    "complete": ((BookingStatus.active,), BookingStatus.completed),
}

STATUS_NAMES = {
    BookingStatus.pending: "ждёт подтверждения",
    BookingStatus.confirmed: "подтверждена",
    BookingStatus.active: "в работе",
    BookingStatus.completed: "завершена",
    BookingStatus.cancelled: "отменена",
    BookingStatus.rejected: "отклонена",
    BookingStatus.expired: "не подтверждена вовремя",
}


def apply_transition(booking: Booking, action: str) -> None:
    allowed_from, target = TRANSITIONS[action]
    if booking.status not in allowed_from:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail=f"Действие недоступно: заявка {STATUS_NAMES[booking.status]}",
        )
    booking.status = target


def ensure_equipment_owner(booking: Booking, user: User) -> None:
    if user.role != UserRole.admin and booking.equipment.owner_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Это заявка не на вашу технику")


# ---------- для клиента ----------


@router.get("/equipment/{equipment_id}/busy", response_model=list[BusyInterval])
async def equipment_busy(
    equipment_id: int,
    session: SessionDep,
    date_from: datetime | None = Query(default=None, alias="from"),
    date_to: datetime | None = Query(default=None, alias="to"),
) -> list[BusyInterval]:
    """Занятые интервалы для календаря. Только время, без данных о клиентах."""
    now = datetime.now(UTC)
    start = date_from or now
    end = date_to or now + timedelta(days=settings.booking_max_days_ahead)
    if end <= start or end - start > timedelta(days=366):
        raise unprocessable("Неверный период")
    rows = await session.execute(
        select(func.lower(Booking.period), func.upper(Booking.period))
        .where(
            Booking.equipment_id == equipment_id,
            Booking.status.in_(BLOCKING),
            Booking.period.op("&&")(Range(start, end, bounds="[)")),
        )
        .order_by(func.lower(Booking.period))
    )
    return [BusyInterval(start=s, end=e) for s, e in rows]


@router.post("/bookings/quote", response_model=QuoteRead)
async def quote_booking(params: BookingParams, session: SessionDep) -> QuoteRead:
    """Предпросмотр: сколько будет стоить и свободно ли время. Ничего не сохраняет."""
    eq, q = await quote_for(session, params)
    return QuoteRead(
        start=q.start,
        end=q.end,
        billable_hours=q.billable_hours,
        total_price=q.total_price,
        available=await is_free(session, eq.id, q.start, q.end),
    )


@router.post("/bookings", response_model=BookingRead, status_code=status.HTTP_201_CREATED)
async def create_booking(
    data: BookingCreate, session: SessionDep, user: CurrentUser, background: BackgroundTasks
) -> BookingRead:
    eq, q = await quote_for(session, data)
    if eq.owner_id == user.id:
        raise unprocessable("Нельзя арендовать собственную технику")

    ensure_normalized(data.delivery_address, data.delivery_address_token)
    booking = Booking(
        user_id=user.id,
        equipment_id=eq.id,
        period=Range(q.start, q.end, bounds="[)"),
        rate_type=data.rate_type.value,
        quantity=data.quantity,
        delivery_address=data.delivery_address or None,
        contact_phone=data.contact_phone,
        comment=data.comment or None,
        rental_price=q.total_price,  # оператор включён: вся сумма — аренда
        total_price=q.total_price,
    )
    session.add(booking)
    if not user.phone:
        user.phone = data.contact_phone  # чтобы в следующий раз не вводить номер заново

    # Проверку «свободно ли» не делаем заранее через SELECT: между проверкой и вставкой
    # кто-то успеет забронировать. Надёжнее вставить и поймать отказ от базы
    try:
        await session.commit()
    except IntegrityError as e:
        await session.rollback()
        if is_exclusion_violation(e):
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                detail="Это время уже занято. Выберите другое начало или длительность",
            ) from None
        raise
    background.add_task(booking_event, booking.id, "created")
    return to_read(await reload(session, booking.id), for_owner=False)


@router.get("/my/bookings", response_model=list[BookingRead])
async def my_bookings(session: SessionDep, user: CurrentUser) -> list[BookingRead]:
    rows = await session.scalars(
        select(Booking)
        .where(Booking.user_id == user.id, Booking.status != BookingStatus.blocked)
        .options(*booking_options())
        .order_by(Booking.created_at.desc())
    )
    return [to_read(b, for_owner=False) for b in rows]


@router.post("/bookings/{booking_id}/cancel", response_model=BookingRead)
async def cancel_booking(
    booking_id: int, session: SessionDep, user: CurrentUser, background: BackgroundTasks
) -> BookingRead:
    booking = await load_booking(session, booking_id)
    if booking.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Заявка не найдена")
    if booking.period.lower <= datetime.now(UTC):
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Аренда уже началась, отменить её на сайте нельзя")
    apply_transition(booking, "cancel")
    await session.commit()
    background.add_task(booking_event, booking.id, "cancelled")
    return to_read(await reload(session, booking.id), for_owner=False)


# ---------- для владельца ----------


@router.get("/owner/bookings", response_model=list[BookingRead])
async def owner_bookings(
    session: SessionDep,
    user: OwnerUser,
    statuses: list[BookingStatus] | None = Query(default=None, alias="status"),
) -> list[BookingRead]:
    stmt = (
        select(Booking)
        .join(Booking.equipment)
        .where(Booking.status != BookingStatus.blocked)  # закрытия владельца — в календаре, не в заявках
        .options(*booking_options())
    )
    if user.role != UserRole.admin:
        stmt = stmt.where(Equipment.owner_id == user.id)
    if statuses:
        stmt = stmt.where(Booking.status.in_(statuses))
    bookings = list(await session.scalars(stmt.order_by(func.lower(Booking.period))))
    return await with_renter_ratings(session, [to_read(b, for_owner=True) for b in bookings])


async def owner_action(booking_id: int, action: str, session: AsyncSession, user: User) -> Booking:
    booking = await load_booking(session, booking_id)
    ensure_equipment_owner(booking, user)
    if action == "confirm" and booking.period.lower <= datetime.now(UTC):
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Время начала уже прошло, заявку нельзя подтвердить")
    apply_transition(booking, action)
    return booking


@router.post("/bookings/{booking_id}/confirm", response_model=BookingRead)
async def confirm_booking(
    booking_id: int, session: SessionDep, user: OwnerUser, background: BackgroundTasks
) -> BookingRead:
    booking = await owner_action(booking_id, "confirm", session, user)
    await session.commit()
    background.add_task(booking_event, booking.id, "confirmed")
    return to_read(await reload(session, booking.id), for_owner=True)


@router.post("/bookings/{booking_id}/reject", response_model=BookingRead)
async def reject_booking(
    booking_id: int, body: RejectBody, session: SessionDep, user: OwnerUser, background: BackgroundTasks
) -> BookingRead:
    booking = await owner_action(booking_id, "reject", session, user)
    booking.reject_reason = (body.reason or "").strip() or None
    await session.commit()
    background.add_task(booking_event, booking.id, "rejected")
    return to_read(await reload(session, booking.id), for_owner=True)


@router.post("/bookings/{booking_id}/start", response_model=BookingRead)
async def start_booking(booking_id: int, session: SessionDep, user: OwnerUser) -> BookingRead:
    booking = await owner_action(booking_id, "start", session, user)
    await session.commit()
    return to_read(await reload(session, booking.id), for_owner=True)


@router.post("/bookings/{booking_id}/complete", response_model=BookingRead)
async def complete_booking(booking_id: int, session: SessionDep, user: OwnerUser) -> BookingRead:
    booking = await owner_action(booking_id, "complete", session, user)
    await session.commit()
    return to_read(await reload(session, booking.id), for_owner=True)
