"""Администрирование: поиск и фильтры по всем записям, удаление насовсем, справочник категорий.

Списки отдаются страницами с фильтрацией на сервере: при тысячах пользователей и броней
грузить всё в браузер нельзя. Любой список можно сузить до одного аккаунта (user_id).
Удаление здесь — именно удаление, без архива.
"""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import ColumnElement, Select, String, cast, exists, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import AdminUser, SessionDep
from app.api.routes.bookings import booking_options, with_renter_ratings
from app.api.routes.bookings import to_read as booking_to_read
from app.api.routes.reviews import review_options
from app.api.routes.reviews import to_read as review_to_read
from app.models import (
    Booking,
    BookingStatus,
    Category,
    Equipment,
    EquipmentStatus,
    Review,
    ReviewDirection,
    User,
    UserRole,
)
from app.schemas.booking import BookingRead
from app.schemas.equipment import CategoryRead, SpecTemplateItem
from app.schemas.review import ReviewRead
from app.services.media import delete_equipment_photo_file
from app.services.slug import slugify

router = APIRouter(prefix="/admin", tags=["admin"])


class Page[T](BaseModel):
    items: list[T]
    total: int


class Paging(BaseModel):
    limit: int
    offset: int


def paging_params(limit: int = Query(default=50, ge=1, le=200), offset: int = Query(default=0, ge=0)) -> Paging:
    # Отдельная зависимость, а не модель в Query: модель нельзя сочетать с другими параметрами запроса
    return Paging(limit=limit, offset=offset)


PagingDep = Annotated[Paging, Depends(paging_params)]


def not_found(what: str) -> HTTPException:
    return HTTPException(status.HTTP_404_NOT_FOUND, detail=f"{what}: запись не найдена")


def like(text: str) -> str:
    """Подстрока для ILIKE с экранированием % и _"""
    escaped = text.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


async def paginate(session: AsyncSession, stmt: Select, paging: Paging) -> tuple[list, int]:
    total = await session.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0
    rows = await session.scalars(stmt.limit(paging.limit).offset(paging.offset))
    return list(rows), total


# ---------- пользователи ----------


class AdminUserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    full_name: str
    phone: str | None
    role: UserRole
    created_at: datetime
    equipment_count: int = 0
    bookings_count: int = 0


@router.get("/users", response_model=Page[AdminUserRead])
async def list_users(
    session: SessionDep,
    _: AdminUser,
    paging: PagingDep,
    q: str | None = Query(default=None, max_length=100, description="Имя, email или телефон"),
    role: UserRole | None = None,
) -> Page[AdminUserRead]:
    stmt = select(User).order_by(User.created_at.desc(), User.id.desc())
    if q and q.strip():
        pattern = like(q)
        digits = "".join(ch for ch in q if ch.isdigit())
        conditions: list[ColumnElement[bool]] = [User.full_name.ilike(pattern), User.email.ilike(pattern)]
        if len(digits) >= 3:  # «8 900 12» находит +7900 12…: сравниваем только цифры
            conditions.append(User.phone.ilike(f"%{digits[1:] if digits[0] in '78' and len(digits) > 3 else digits}%"))
        stmt = stmt.where(or_(*conditions))
    if role:
        stmt = stmt.where(User.role == role)
    users, total = await paginate(session, stmt, paging)

    ids = [u.id for u in users]
    eq_counts = (
        dict(
            (
                await session.execute(
                    select(Equipment.owner_id, func.count())
                    .where(Equipment.owner_id.in_(ids))
                    .group_by(Equipment.owner_id)
                )
            ).all()
        )
        if ids
        else {}
    )
    bk_counts = (
        dict(
            (
                await session.execute(
                    select(Booking.user_id, func.count()).where(Booking.user_id.in_(ids)).group_by(Booking.user_id)
                )
            ).all()
        )
        if ids
        else {}
    )
    items = []
    for u in users:
        item = AdminUserRead.model_validate(u)
        item.equipment_count, item.bookings_count = eq_counts.get(u.id, 0), bk_counts.get(u.id, 0)
        items.append(item)
    return Page(items=items, total=total)


async def photo_files(session: AsyncSession, *conditions) -> list[str]:
    rows = await session.scalars(select(Equipment).where(*conditions).options(selectinload(Equipment.photos)))
    return [p.filename for eq in rows for p in eq.photos]


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: int, session: SessionDep, admin: AdminUser) -> None:
    if user_id == admin.id:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Нельзя удалить собственный аккаунт")
    user = await session.get(User, user_id)
    if user is None:
        raise not_found("Пользователь")
    files = await photo_files(session, Equipment.owner_id == user_id)
    await session.delete(user)  # каскадом уходят его техника, брони и отзывы
    await session.commit()
    for name in files:
        delete_equipment_photo_file(name)


# ---------- техника ----------


class AdminEquipmentRead(BaseModel):
    id: int
    name: str
    category: str
    status: str
    owner_id: int
    owner_name: str
    owner_email: str
    created_at: datetime


@router.get("/equipment", response_model=Page[AdminEquipmentRead])
async def list_equipment(
    session: SessionDep,
    _: AdminUser,
    paging: PagingDep,
    q: str | None = Query(default=None, max_length=100, description="Название техники"),
    status_: EquipmentStatus | None = Query(default=None, alias="status"),
    category: str | None = Query(default=None, description="slug категории"),
    user_id: int | None = Query(default=None, description="Только техника этого владельца"),
) -> Page[AdminEquipmentRead]:
    stmt = (
        select(Equipment)
        .options(selectinload(Equipment.owner), selectinload(Equipment.category))
        .order_by(Equipment.created_at.desc(), Equipment.id.desc())
    )
    if q and q.strip():
        stmt = stmt.where(Equipment.name.ilike(like(q)))
    if status_:
        stmt = stmt.where(Equipment.status == status_)
    if category:
        stmt = stmt.where(Equipment.category.has(Category.slug == category))
    if user_id:
        stmt = stmt.where(Equipment.owner_id == user_id)
    rows, total = await paginate(session, stmt, paging)
    return Page(
        items=[
            AdminEquipmentRead(
                id=e.id,
                name=e.name,
                category=e.category.name,
                status=e.status,
                owner_id=e.owner_id,
                owner_name=e.owner.full_name,
                owner_email=e.owner.email,
                created_at=e.created_at,
            )
            for e in rows
        ],
        total=total,
    )


@router.delete("/equipment/{equipment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_equipment(equipment_id: int, session: SessionDep, _: AdminUser) -> None:
    """В отличие от владельца, администратор удаляет технику и с активными бронями"""
    eq = await session.get(Equipment, equipment_id)
    if eq is None:
        raise not_found("Техника")
    files = await photo_files(session, Equipment.id == equipment_id)
    await session.delete(eq)
    await session.commit()
    for name in files:
        delete_equipment_photo_file(name)


# ---------- брони ----------


@router.get("/bookings", response_model=Page[BookingRead])
async def list_bookings(
    session: SessionDep,
    _: AdminUser,
    paging: PagingDep,
    q: str | None = Query(default=None, max_length=100, description="Техника, клиент или номер брони"),
    statuses: list[BookingStatus] | None = Query(default=None, alias="status"),
    user_id: int | None = Query(default=None, description="Брони этого аккаунта: как клиента или как владельца"),
) -> Page[BookingRead]:
    stmt = (
        select(Booking)
        .join(Booking.equipment)
        .join(Booking.user)
        .options(*booking_options())
        .order_by(Booking.created_at.desc(), Booking.id.desc())
    )
    if q and q.strip():
        pattern = like(q)
        stmt = stmt.where(
            or_(
                Equipment.name.ilike(pattern),
                User.full_name.ilike(pattern),
                User.email.ilike(pattern),
                cast(Booking.id, String) == q.strip().lstrip("#"),
            )
        )
    if statuses:
        stmt = stmt.where(Booking.status.in_(statuses))
    if user_id:
        stmt = stmt.where(or_(Booking.user_id == user_id, Equipment.owner_id == user_id))
    rows, total = await paginate(session, stmt, paging)
    items = await with_renter_ratings(session, [booking_to_read(b, for_owner=True) for b in rows])
    return Page(items=items, total=total)


@router.delete("/bookings/{booking_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_booking(booking_id: int, session: SessionDep, _: AdminUser) -> None:
    booking = await session.get(Booking, booking_id)
    if booking is None:
        raise not_found("Бронь")
    await session.delete(booking)  # время сразу освобождается, отзывы по брони удаляются каскадом
    await session.commit()


# ---------- отзывы ----------


class AdminReviewRead(ReviewRead):
    subject_id: int
    subject_name: str
    author_id: int


@router.get("/reviews", response_model=Page[AdminReviewRead])
async def list_reviews(
    session: SessionDep,
    _: AdminUser,
    paging: PagingDep,
    direction: ReviewDirection | None = None,
    max_rating: int | None = Query(default=None, ge=1, le=5, description="Например, 2 — только плохие отзывы"),
    user_id: int | None = Query(default=None, description="Отзывы этого аккаунта: о нём или от него"),
) -> Page[AdminReviewRead]:
    stmt = (
        select(Review)
        .options(*review_options(), selectinload(Review.subject))
        .order_by(Review.created_at.desc(), Review.id.desc())
    )
    if direction:
        stmt = stmt.where(Review.direction == direction)
    if max_rating:
        stmt = stmt.where(Review.rating <= max_rating)
    if user_id:
        stmt = stmt.where(or_(Review.subject_id == user_id, Review.author_id == user_id))
    rows, total = await paginate(session, stmt, paging)
    return Page(
        items=[
            AdminReviewRead(
                **review_to_read(r).model_dump(),
                subject_id=r.subject_id,
                subject_name=r.subject.full_name,
                author_id=r.author_id,
            )
            for r in rows
        ],
        total=total,
    )


@router.delete("/reviews/{review_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_review(review_id: int, session: SessionDep, _: AdminUser) -> None:
    review = await session.get(Review, review_id)
    if review is None:
        raise not_found("Отзыв")
    await session.delete(review)
    await session.commit()


# ---------- категории ----------


class CategoryWrite(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=2, max_length=100)
    spec_template: list[SpecTemplateItem] = Field(default=[], max_length=15)

    @field_validator("spec_template")
    @classmethod
    def unique_names(cls, v: list[SpecTemplateItem]) -> list[SpecTemplateItem]:
        seen: dict[str, SpecTemplateItem] = {}
        for item in v:
            seen.setdefault(item.name, item)
        return list(seen.values())


def template_json(data: CategoryWrite) -> list[dict]:
    return [{"name": i.name, "example": i.example or None} for i in data.spec_template]


async def unique_slug(session: AsyncSession, name: str, exclude_id: int | None = None) -> str:
    base = slugify(name)
    slug, n = base, 2
    while await session.scalar(select(exists().where(Category.slug == slug, Category.id != (exclude_id or 0)))):
        slug, n = f"{base}-{n}", n + 1
    return slug


def name_taken() -> HTTPException:
    return HTTPException(status.HTTP_409_CONFLICT, detail="Категория с таким названием уже есть")


@router.post("/categories", response_model=CategoryRead, status_code=status.HTTP_201_CREATED)
async def create_category(data: CategoryWrite, session: SessionDep, _: AdminUser) -> Category:
    category = Category(name=data.name, slug=await unique_slug(session, data.name), spec_template=template_json(data))
    session.add(category)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise name_taken() from None
    return category


@router.put("/categories/{category_id}", response_model=CategoryRead)
async def update_category(category_id: int, data: CategoryWrite, session: SessionDep, _: AdminUser) -> Category:
    category = await session.get(Category, category_id)
    if category is None:
        raise not_found("Категория")
    # slug не меняем: на него могут вести сохранённые ссылки на каталог
    category.name = data.name
    category.spec_template = template_json(data)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise name_taken() from None
    return category


@router.delete("/categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(category_id: int, session: SessionDep, _: AdminUser) -> None:
    category = await session.get(Category, category_id)
    if category is None:
        raise not_found("Категория")
    if await session.scalar(select(exists().where(Equipment.category_id == category_id))):
        raise HTTPException(
            status.HTTP_409_CONFLICT, detail="В категории есть техника. Сначала перенесите её в другую категорию"
        )
    await session.delete(category)
    await session.commit()
