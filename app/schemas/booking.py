from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models import BookingStatus, RateType
from app.schemas.equipment import Amount

PHONE_PATTERN = r"^\+?[\d\s()\-]{10,20}$"


class BookingParams(BaseModel):
    equipment_id: int
    rate_type: RateType
    start: datetime = Field(description="Начало первой смены или часа, с часовым поясом")
    quantity: int = Field(ge=1, le=30, description="Часы или смены")
    with_operator: bool = False

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

    contact_phone: str = Field(pattern=PHONE_PATTERN, description="По нему позвонит владелец")
    delivery_address: str | None = Field(default=None, max_length=500)
    comment: str | None = Field(default=None, max_length=1000)


class QuoteRead(BaseModel):
    start: datetime
    end: datetime
    billable_hours: int
    rental_price: Amount
    operator_price: Amount
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
    full_name: str
    phone: str | None


class BookingRead(BaseModel):
    id: int
    status: BookingStatus
    rate_type: RateType
    quantity: int
    start: datetime
    end: datetime
    with_operator: bool
    delivery_address: str | None
    comment: str | None
    contact_phone: str
    reject_reason: str | None
    rental_price: Amount
    operator_price: Amount
    total_price: Amount
    created_at: datetime
    equipment: BookingEquipment
    client: Contact | None = Field(default=None, description="Для владельца: кто арендует")
    owner: Contact | None = Field(
        default=None, description="Для клиента: контакт владельца после подтверждения"
    )
