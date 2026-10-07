from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.equipment import Equipment


class EquipmentPhoto(Base):
    __tablename__ = "equipment_photos"

    id: Mapped[int] = mapped_column(primary_key=True)
    equipment_id: Mapped[int] = mapped_column(
        ForeignKey("equipment.id", ondelete="CASCADE"), index=True
    )
    # Имя файла в MEDIA_DIR/equipment, например "3f2a...c1.webp"
    filename: Mapped[str] = mapped_column(String(64), unique=True)
    position: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    equipment: Mapped["Equipment"] = relationship(back_populates="photos", lazy="raise")

    @property
    def url(self) -> str:
        return f"/media/equipment/{self.filename}"
