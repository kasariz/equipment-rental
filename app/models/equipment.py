import enum
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.category import Category
    from app.models.photo import EquipmentPhoto
    from app.models.user import User


class EquipmentStatus(str, enum.Enum):
    available = "available"
    maintenance = "maintenance"  # на ремонте/ТО
    inactive = "inactive"  # снята с размещения


class Equipment(Base):
    __tablename__ = "equipment"
    __table_args__ = (
        CheckConstraint("price_per_hour > 0", name="price_per_hour_positive"),
        CheckConstraint("min_hours >= 1", name="min_hours_positive"),
        CheckConstraint("latitude BETWEEN -90 AND 90", name="latitude_range"),
        CheckConstraint("longitude BETWEEN -180 AND 180", name="longitude_range"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"), index=True)

    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    # У разной техники разные характеристики: глубина копания, грузоподъёмность, вылет стрелы...
    # Список [{"name": ..., "value": ...}], а не объект: JSONB не сохраняет порядок ключей
    specs: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list, server_default="[]")

    # Где техника базируется: показываем арендатору и считаем расстояние
    address: Mapped[str | None] = mapped_column(String(255))
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)

    price_per_hour: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    price_per_shift: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))  # смена = 8 часов
    min_hours: Mapped[int] = mapped_column(Integer, default=4, server_default="4")

    operator_available: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    operator_price_per_hour: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))

    status: Mapped[EquipmentStatus] = mapped_column(
        Enum(EquipmentStatus, name="equipment_status"),
        default=EquipmentStatus.available,
        server_default=EquipmentStatus.available.value,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    category: Mapped["Category"] = relationship(lazy="raise")
    owner: Mapped["User"] = relationship(lazy="raise")
    photos: Mapped[list["EquipmentPhoto"]] = relationship(
        back_populates="equipment",
        order_by="(EquipmentPhoto.position, EquipmentPhoto.id)",
        cascade="all, delete-orphan",
        lazy="raise",
    )
