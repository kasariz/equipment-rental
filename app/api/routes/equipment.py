from datetime import datetime
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, UploadFile, status
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import ColumnElement, bindparam, exists, func, literal, select
from sqlalchemy.dialects.postgresql import TSTZRANGE, Range
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import OptionalUser, OwnerUser, SessionDep
from app.api.routes.geo import ensure_normalized
from app.core.config import settings
from app.models import (
    Booking,
    BookingStatus,
    Category,
    Equipment,
    EquipmentPhoto,
    EquipmentStatus,
    User,
    UserRole,
)
from app.schemas.equipment import (
    CategoryRead,
    EquipmentCreate,
    EquipmentListItem,
    EquipmentPage,
    EquipmentRead,
    EquipmentUpdate,
    PhotoRead,
    SortOption,
)
from app.services.media import delete_equipment_photo_file, save_equipment_photo
from app.services.ratings import owner_rating, ratings_subquery

router = APIRouter(tags=["catalog"])

# Брони, которые занимают технику (совпадает с условием ограничения bookings_no_overlap)
BLOCKING_STATUSES = (BookingStatus.pending, BookingStatus.confirmed, BookingStatus.active)


# ---------- вспомогательное ----------


def distance_km(lat: float, lon: float) -> ColumnElement[float]:
    """Расстояние по сфере (формула косинусов). Для тысяч объектов хватает,
    для сотен тысяч стоит перейти на PostGIS с пространственным индексом."""
    lat_r, lon_r = func.radians(literal(lat)), func.radians(literal(lon))
    cos_angle = func.cos(lat_r) * func.cos(func.radians(Equipment.latitude)) * func.cos(
        func.radians(Equipment.longitude) - lon_r
    ) + func.sin(lat_r) * func.sin(func.radians(Equipment.latitude))
    # least/greatest страхуют acos от погрешности округления чуть за пределы [-1, 1]
    return 6371 * func.acos(func.least(1.0, func.greatest(-1.0, cos_angle)))


def to_list_item(
    eq: Equipment, distance: float | None = None, rating: float | None = None, reviews_count: int | None = None
) -> EquipmentListItem:
    item = EquipmentListItem.model_validate(eq)
    item.cover_url = eq.photos[0].url if eq.photos else None
    item.distance_km = round(distance, 1) if distance is not None else None
    item.owner_rating = round(float(rating), 1) if rating is not None else None
    item.owner_reviews_count = reviews_count or 0
    return item


async def to_read(session: AsyncSession, eq: Equipment) -> EquipmentRead:
    item = EquipmentRead.model_validate(eq)
    item.cover_url = eq.photos[0].url if eq.photos else None
    item.owner.rating, item.owner.reviews_count = await owner_rating(session, eq.owner_id)
    item.owner_rating, item.owner_reviews_count = item.owner.rating, item.owner.reviews_count
    return item


async def load_equipment(session: AsyncSession, equipment_id: int) -> Equipment | None:
    return await session.scalar(
        select(Equipment)
        .where(Equipment.id == equipment_id)
        .options(
            selectinload(Equipment.category),
            selectinload(Equipment.photos),
            selectinload(Equipment.owner),
        )
        .execution_options(populate_existing=True)
    )


def can_manage(user: User | None, eq: Equipment) -> bool:
    return user is not None and (user.id == eq.owner_id or user.role == UserRole.admin)


async def get_managed_equipment(session: AsyncSession, equipment_id: int, user: User) -> Equipment:
    eq = await load_equipment(session, equipment_id)
    if eq is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Техника не найдена")
    if not can_manage(user, eq):
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Это не ваша техника")
    return eq


async def ensure_category_exists(session: AsyncSession, category_id: int) -> None:
    if await session.get(Category, category_id) is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Такой категории нет")


# ---------- публичный каталог ----------


class EquipmentFilters(BaseModel):
    category: str | None = Field(default=None, description="slug категории")
    q: str | None = Field(default=None, max_length=100, description="Поиск по названию")
    price_max: Decimal | None = Field(default=None, gt=0, description="Максимальная цена за час")
    lat: float | None = Field(default=None, ge=-90, le=90)
    lon: float | None = Field(default=None, ge=-180, le=180)
    radius_km: float | None = Field(default=None, gt=0, le=500)
    available_from: datetime | None = None
    available_to: datetime | None = None
    sort: SortOption = "new"
    limit: int = Field(default=100, ge=1, le=500)
    offset: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def check_combinations(self) -> "EquipmentFilters":
        has_point = self.lat is not None and self.lon is not None
        if (self.lat is None) != (self.lon is None):
            raise ValueError("Передайте и lat, и lon")
        if (self.radius_km is not None or self.sort == "distance") and not has_point:
            raise ValueError("Для поиска по расстоянию нужна точка: lat и lon")
        if (self.available_from is None) != (self.available_to is None):
            raise ValueError("Передайте обе даты: available_from и available_to")
        if self.available_from and self.available_to:
            if self.available_from.tzinfo is None or self.available_to.tzinfo is None:
                raise ValueError("Даты должны быть с часовым поясом")
            if self.available_from >= self.available_to:
                raise ValueError("Начало периода должно быть раньше конца")
        return self


@router.get("/categories", response_model=list[CategoryRead])
async def list_categories(session: SessionDep) -> list[Category]:
    return list(await session.scalars(select(Category).order_by(Category.id)))


@router.get("/equipment", response_model=EquipmentPage)
async def list_equipment(session: SessionDep, filters: Annotated[EquipmentFilters, Query()]) -> EquipmentPage:
    f = filters
    conditions: list[ColumnElement[bool]] = [Equipment.status == EquipmentStatus.available]

    if f.category:
        conditions.append(Equipment.category.has(Category.slug == f.category))
    if f.q:
        conditions.append(Equipment.name.icontains(f.q.strip(), autoescape=True))
    if f.price_max is not None:
        conditions.append(Equipment.price_per_hour <= f.price_max)

    dist = distance_km(f.lat, f.lon) if f.lat is not None and f.lon is not None else None
    if dist is not None and f.radius_km is not None:
        conditions.append(dist <= f.radius_km)

    if f.available_from and f.available_to:
        # Свободна, если нет ни одной занимающей брони, пересекающейся с периодом.
        # Проверка идёт по тому же GiST-индексу, что и ограничение от двойного бронирования
        period = bindparam("period", Range(f.available_from, f.available_to, bounds="[)"), type_=TSTZRANGE)
        conditions.append(
            ~exists().where(
                Booking.equipment_id == Equipment.id,
                Booking.status.in_(BLOCKING_STATUSES),
                Booking.period.op("&&")(period),
            )
        )

    total = await session.scalar(select(func.count(Equipment.id)).where(*conditions)) or 0

    order_by = {
        "new": [Equipment.created_at.desc()],
        "price_asc": [Equipment.price_per_hour.asc()],
        "price_desc": [Equipment.price_per_hour.desc()],
        "distance": [dist.asc()] if dist is not None else [],
    }[f.sort]

    ratings = ratings_subquery()
    stmt = (
        select(
            Equipment,
            dist.label("distance") if dist is not None else literal(None),
            ratings.c.rating,
            ratings.c.reviews_count,
        )
        .outerjoin(ratings, ratings.c.subject_id == Equipment.owner_id)
        .where(*conditions)
        .options(selectinload(Equipment.category), selectinload(Equipment.photos))
        .order_by(*order_by, Equipment.id)
        .limit(f.limit)
        .offset(f.offset)
    )
    rows = (await session.execute(stmt)).all()
    return EquipmentPage(items=[to_list_item(eq, d, r, c) for eq, d, r, c in rows], total=total)


@router.get("/equipment/{equipment_id}", response_model=EquipmentRead)
async def get_equipment(equipment_id: int, session: SessionDep, user: OptionalUser) -> EquipmentRead:
    eq = await load_equipment(session, equipment_id)
    # Снятую с размещения технику видят только владелец и админ
    if eq is None or (eq.status != EquipmentStatus.available and not can_manage(user, eq)):
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Техника не найдена")
    return await to_read(session, eq)


# ---------- кабинет владельца ----------


@router.get("/my/equipment", response_model=list[EquipmentListItem])
async def list_my_equipment(session: SessionDep, user: OwnerUser) -> list[EquipmentListItem]:
    rows = await session.scalars(
        select(Equipment)
        .where(Equipment.owner_id == user.id)
        .options(selectinload(Equipment.category), selectinload(Equipment.photos))
        .order_by(Equipment.created_at.desc())
    )
    return [to_list_item(eq) for eq in rows]


@router.post("/equipment", response_model=EquipmentRead, status_code=status.HTTP_201_CREATED)
async def create_equipment(data: EquipmentCreate, session: SessionDep, user: OwnerUser) -> EquipmentRead:
    await ensure_category_exists(session, data.category_id)
    ensure_normalized(data.address, data.address_token)
    eq = Equipment(**data.model_dump(exclude={"address_token"}), owner_id=user.id)
    session.add(eq)
    await session.commit()
    created = await load_equipment(session, eq.id)
    assert created is not None
    return await to_read(session, created)


@router.patch("/equipment/{equipment_id}", response_model=EquipmentRead)
async def update_equipment(
    equipment_id: int, data: EquipmentUpdate, session: SessionDep, user: OwnerUser
) -> EquipmentRead:
    eq = await get_managed_equipment(session, equipment_id, user)
    changes = data.model_dump(exclude_unset=True)
    token = changes.pop("address_token", None)
    if "address" in changes:
        ensure_normalized(changes["address"], token)

    if changes.get("category_id") is not None:
        await ensure_category_exists(session, changes["category_id"])
    # Обязательные поля нельзя «обнулить» через PATCH
    for field in (
        "name",
        "category_id",
        "latitude",
        "longitude",
        "price_per_hour",
        "min_hours",
        "status",
        "address",
        "specs",
    ):
        if field in changes and changes[field] is None:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, detail=f"Поле {field} не может быть пустым")

    for field, value in changes.items():
        setattr(eq, field, value)

    await session.commit()
    updated = await load_equipment(session, eq.id)
    assert updated is not None
    return await to_read(session, updated)


@router.delete("/equipment/{equipment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_equipment(equipment_id: int, session: SessionDep, user: OwnerUser) -> None:
    eq = await get_managed_equipment(session, equipment_id, user)
    has_bookings = await session.scalar(
        select(exists().where(Booking.equipment_id == eq.id, Booking.status.in_(BLOCKING_STATUSES)))
    )
    if has_bookings:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail="У техники есть активные брони. Снимите её с размещения вместо удаления",
        )
    filenames = [p.filename for p in eq.photos]
    await session.delete(eq)
    await session.commit()
    for name in filenames:
        delete_equipment_photo_file(name)


@router.post(
    "/equipment/{equipment_id}/photos",
    response_model=list[PhotoRead],
    status_code=status.HTTP_201_CREATED,
)
async def upload_photos(
    equipment_id: int, files: list[UploadFile], session: SessionDep, user: OwnerUser
) -> list[EquipmentPhoto]:
    eq = await get_managed_equipment(session, equipment_id, user)
    limit = settings.max_photos_per_equipment
    if len(eq.photos) + len(files) > limit:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Можно загрузить не больше {limit} фото, сейчас уже {len(eq.photos)}",
        )

    saved: list[str] = []
    try:
        for upload in files:
            saved.append(await save_equipment_photo(upload))
    except HTTPException:
        for name in saved:  # одна битая картинка — не сохраняем и остальные из этой пачки
            delete_equipment_photo_file(name)
        raise

    start = max((p.position for p in eq.photos), default=-1) + 1
    for i, name in enumerate(saved):
        eq.photos.append(EquipmentPhoto(filename=name, position=start + i))
    await session.commit()

    refreshed = await load_equipment(session, eq.id)
    assert refreshed is not None
    return refreshed.photos


@router.delete("/equipment/{equipment_id}/photos/{photo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_photo(equipment_id: int, photo_id: int, session: SessionDep, user: OwnerUser) -> None:
    eq = await get_managed_equipment(session, equipment_id, user)
    photo = next((p for p in eq.photos if p.id == photo_id), None)
    if photo is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Фото не найдено")
    eq.photos.remove(photo)
    await session.commit()
    delete_equipment_photo_file(photo.filename)
