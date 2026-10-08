from typing import Any

from sqlalchemy import String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Category(Base):
    """Экскаваторы, погрузчики, автокраны и т. д. Новые категории добавляет администратор"""

    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    slug: Mapped[str] = mapped_column(String(100), unique=True)
    # Характеристики, которые предлагаются владельцу: [{"name": "Масса", "example": "8 т"}, ...]
    spec_template: Mapped[list[Any]] = mapped_column(JSONB, default=list, server_default="[]")
