import enum
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Enum, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class UserRole(enum.StrEnum):
    client = "client"  # арендатор
    owner = "owner"  # владелец техники
    admin = "admin"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(32))
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role"),
        default=UserRole.client,
        server_default=UserRole.client.value,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Telegram: id чата для уведомлений и одноразовый код привязки из ссылки t.me/<бот>?start=<код>
    telegram_chat_id: Mapped[int | None] = mapped_column(BigInteger, unique=True)
    telegram_link_code: Mapped[str | None] = mapped_column(String(64), unique=True)
    telegram_link_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    @property
    def telegram_connected(self) -> bool:
        return self.telegram_chat_id is not None
