from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    PlainSerializer,
    model_validator,
)

from app.models import EquipmentStatus

# Деньги считаем в Decimal, а в JSON отдаём числом, чтобы фронту не парсить строки
Money = Annotated[
    Decimal,
    Field(gt=0, max_digits=10, decimal_places=2),
    PlainSerializer(float, return_type=float, when_used="json"),
]

# Суммы в бронях: могут быть нулевыми (например, оператор не нужен)
Amount = Annotated[
    Decimal,
    Field(ge=0, max_digits=12, decimal_places=2),
    PlainSerializer(float, return_type=float, when_used="json"),
]


class SpecItem(BaseModel):
    """Характеристика: «Глубина копания» → «5,9 м». Строки, потому что так их пишут люди."""

    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=100)
    value: str = Field(min_length=1, max_length=200)


Specs = Annotated[list[SpecItem], Field(max_length=30)]


class CategoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str


class PhotoRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    url: str


class OwnerPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str


class EquipmentFields(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    category_id: int
    description: str | None = Field(default=None, max_length=5000)
    specs: Specs = []
    address: str | None = Field(default=None, max_length=255)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    price_per_hour: Money
    price_per_shift: Money | None = None
    min_hours: int = Field(default=4, ge=1, le=24)
    operator_available: bool = False
    operator_price_per_hour: Money | None = None


def _check_operator_price(operator_available: bool, price: Decimal | None) -> None:
    if operator_available and price is None:
        raise ValueError("Укажите цену оператора за час")


class EquipmentCreate(EquipmentFields):
    @model_validator(mode="after")
    def operator_price_required(self) -> "EquipmentCreate":
        _check_operator_price(self.operator_available, self.operator_price_per_hour)
        return self


class EquipmentUpdate(BaseModel):
    """PATCH: передаются только изменённые поля."""

    name: str | None = Field(default=None, min_length=2, max_length=255)
    category_id: int | None = None
    description: str | None = Field(default=None, max_length=5000)
    specs: Specs | None = None
    address: str | None = Field(default=None, max_length=255)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    price_per_hour: Money | None = None
    price_per_shift: Money | None = None
    min_hours: int | None = Field(default=None, ge=1, le=24)
    operator_available: bool | None = None
    operator_price_per_hour: Money | None = None
    status: EquipmentStatus | None = None


class EquipmentListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    category: CategoryRead
    address: str | None
    latitude: float
    longitude: float
    price_per_hour: Money
    price_per_shift: Money | None
    min_hours: int
    operator_available: bool
    operator_price_per_hour: Money | None
    status: EquipmentStatus
    cover_url: str | None = None
    distance_km: float | None = None


class EquipmentRead(EquipmentListItem):
    description: str | None
    specs: list[SpecItem]
    photos: list[PhotoRead]
    owner: OwnerPublic
    created_at: datetime


class EquipmentPage(BaseModel):
    items: list[EquipmentListItem]
    total: int


SortOption = Literal["new", "price_asc", "price_desc", "distance"]
