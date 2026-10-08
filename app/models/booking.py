import enum
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import TSTZRANGE, ExcludeConstraint, Range
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.equipment import Equipment
    from app.models.review import Review
    from app.models.user import User


class BookingStatus(enum.StrEnum):
    pending = "pending"  # клиент оставил заявку, ждёт звонка владельца
    confirmed = "confirmed"  # владелец созвонился и подтвердил
    active = "active"  # техника в работе
    completed = "completed"
    cancelled = "cancelled"  # отменил клиент
    rejected = "rejected"  # отклонил владелец
    expired = "expired"  # владелец не подтвердил вовремя


class RateType(enum.StrEnum):
    hourly = "hourly"  # quantity = часы
    shift = "shift"  # quantity = смены по 8 часов, по одной в день


class Booking(Base):
    __tablename__ = "bookings"
    __table_args__ = (
        # Одну технику нельзя забронировать на пересекающиеся периоды.
        # Заявка, ждущая звонка, тоже держит время: иначе владелец будет звонить
        # двум клиентам на один слот. Отменённые и закрытые в проверке не участвуют.
        # Требует расширения btree_gist (создаётся в первой миграции).
        ExcludeConstraint(
            ("equipment_id", "="),
            ("period", "&&"),
            using="gist",
            where=text("status IN ('pending', 'confirmed', 'active')"),
            name="bookings_no_overlap",
        ),
        CheckConstraint("NOT isempty(period)", name="period_not_empty"),
        CheckConstraint("total_price >= 0", name="total_price_non_negative"),
        CheckConstraint("rate_type IN ('hourly', 'shift')", name="rate_type_valid"),
        CheckConstraint("quantity > 0", name="quantity_positive"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    equipment_id: Mapped[int] = mapped_column(ForeignKey("equipment.id", ondelete="CASCADE"), index=True)

    # Полуоткрытый интервал [начало, конец): аренда 10:00–14:00 не конфликтует с 14:00–18:00
    period: Mapped[Range[datetime]] = mapped_column(TSTZRANGE)
    rate_type: Mapped[str] = mapped_column(String(16), server_default=RateType.hourly.value)
    quantity: Mapped[int] = mapped_column(Integer, server_default="1")

    delivery_address: Mapped[str | None] = mapped_column(String(500))
    contact_phone: Mapped[str] = mapped_column(String(32))
    comment: Mapped[str | None] = mapped_column(Text)
    reject_reason: Mapped[str | None] = mapped_column(String(500))

    # Цена фиксируется в момент заявки: если владелец потом поменяет прайс, бронь не изменится
    rental_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), server_default="0")
    total_price: Mapped[Decimal] = mapped_column(Numeric(12, 2))

    status: Mapped[BookingStatus] = mapped_column(
        Enum(BookingStatus, name="booking_status"),
        default=BookingStatus.pending,
        server_default=BookingStatus.pending.value,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped["User"] = relationship(lazy="raise")
    equipment: Mapped["Equipment"] = relationship(lazy="raise")
    reviews: Mapped[list["Review"]] = relationship(back_populates="booking", lazy="raise")
