import enum
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, SmallInteger, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.booking import Booking
    from app.models.user import User


class ReviewDirection(enum.StrEnum):
    about_owner = "about_owner"  # арендатор оценивает владельца
    about_renter = "about_renter"  # владелец оценивает арендатора


class Review(Base):
    """Отзыв по брони. По каждой брони — не больше одного отзыва в каждую сторону"""

    __tablename__ = "reviews"
    __table_args__ = (
        CheckConstraint("rating BETWEEN 1 AND 5", name="rating_range"),
        CheckConstraint("direction IN ('about_owner', 'about_renter')", name="direction_valid"),
        UniqueConstraint("booking_id", "direction", name="uq_reviews_booking_id_direction"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    booking_id: Mapped[int] = mapped_column(ForeignKey("bookings.id", ondelete="CASCADE"))
    direction: Mapped[str] = mapped_column(String(16), server_default=ReviewDirection.about_owner.value)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    # Тот, о ком отзыв: владелец или арендатор
    subject_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    rating: Mapped[int] = mapped_column(SmallInteger)
    text: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    author: Mapped["User"] = relationship(foreign_keys=[author_id], lazy="raise")
    subject: Mapped["User"] = relationship(foreign_keys=[subject_id], lazy="raise")
    booking: Mapped["Booking"] = relationship(back_populates="reviews", lazy="raise")
