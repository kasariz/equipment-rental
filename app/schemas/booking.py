from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.phone import Phone
from app.models import BookingStatus, RateType
from app.schemas.equipment import Amount


class BookingParams(BaseModel):
    equipment_id: int
    rate_type: RateType
    start: datetime = Field(description="Начало первой смены или часа, с часовым поясом")
    quantity: int = Field(ge=1, le=30, description="Часы или смены")

    @field_validator("start")
    @classmethod
    def whole_hour_with_tz(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            raise ValueError("Время начала должно быть с часовым поясом")
        if v.minute or v.second or v.microsecond:
            raise ValueError("Аренда начинается в начале часа")
        return v


class BookingCreate(BookingParams):
    model_config = ConfigDict(str_strip_whitespace=True)

    contact_phone: Phone = Field(description="По нему позвонит владелец")
    delivery_address: str | None = Field(default=None, max_length=500)
    delivery_address_token: str | None = Field(default=None, description="Подпись адреса из /api/geo/search")
    comment: str | None = Field(default=None, max_length=1000)


class QuoteRead(BaseModel):
    start: datetime
    end: datetime
    billable_hours: int
    total_price: Amount
    available: bool


class RejectBody(BaseModel):
    reason: str | None = Field(default=None, max_length=500)


class BusyInterval(BaseModel):
    start: datetime
    end: datetime


class BookingEquipment(BaseModel):
    id: int
    name: str
    category: str
    address: str | None
    cover_url: str | None


class Contact(BaseModel):
    id: int | None = None
    full_name: str
    phone: str | None
    # Для владельца: рейтинг арендатора по отзывам других владельцев
    rating: float | None = None
    reviews_count: int = 0


class BookingRead(BaseModel):
    id: int
    status: BookingStatus
    rate_type: RateType
    quantity: int
    start: datetime
    end: datetime
    delivery_address: str | None
    comment: str | None
    contact_phone: str
    reject_reason: str | None
    total_price: Amount
    created_at: datetime
    reviewed: bool = Field(default=False, description="Клиент уже оставил отзыв о владельце")
    renter_reviewed: bool = Field(default=False, description="Владелец уже оставил отзыв об арендаторе")
    equipment: BookingEquipment
    client: Contact | None = Field(default=None, description="Для владельца: кто арендует")
    owner: Contact | None = Field(default=None, description="Для клиента: контакт владельца после подтверждения")
