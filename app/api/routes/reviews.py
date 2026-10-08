"""Отзывы в обе стороны.

Арендатор оценивает владельца после завершённой аренды или если владелец отклонил заявку
(либо отменил уже подтверждённую бронь). Владелец оценивает арендатора после завершённой
аренды или если арендатор отменил бронь.
"""

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUser, OwnerUser, SessionDep
from app.models import Booking, BookingStatus, Review, ReviewDirection, User, UserRole
from app.schemas.review import MyRatings, ReviewCreate, ReviewRead, UserReviews, UserReviewsSummary
from app.services.ratings import user_rating

router = APIRouter(tags=["reviews"])

# После каких исходов брони можно оставить отзыв
REVIEWABLE = {
    ReviewDirection.about_owner: (BookingStatus.completed, BookingStatus.rejected),
    ReviewDirection.about_renter: (BookingStatus.completed, BookingStatus.cancelled),
}


def short_name(full_name: str) -> str:
    """«Анна Клиентова» → «Анна К.»: полное имя автора отзыва показывать незачем"""
    parts = full_name.split()
    return f"{parts[0]} {parts[1][0]}." if len(parts) > 1 else parts[0]


def to_read(r: Review) -> ReviewRead:
    return ReviewRead(
        id=r.id,
        direction=r.direction,
        rating=r.rating,
        text=r.text,
        created_at=r.created_at,
        author_name=short_name(r.author.full_name),
        equipment_name=r.booking.equipment.name,
    )


def review_options():
    return (selectinload(Review.author), selectinload(Review.booking).selectinload(Booking.equipment))


async def add_review(
    session: AsyncSession, booking: Booking, direction: ReviewDirection, author: User, data: ReviewCreate
) -> ReviewRead:
    if booking.status not in REVIEWABLE[direction]:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail="Отзыв можно оставить после завершения аренды или отмены брони другой стороной",
        )
    subject_id = booking.equipment.owner_id if direction == ReviewDirection.about_owner else booking.user_id
    review = Review(
        booking_id=booking.id,
        direction=direction,
        author_id=author.id,
        subject_id=subject_id,
        rating=data.rating,
        text=data.text or None,
    )
    session.add(review)
    try:
        await session.commit()
    except IntegrityError:  # уникальность (booking_id, direction): второй отзыв в ту же сторону
        await session.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Отзыв по этой брони уже оставлен") from None
    created = await session.scalar(select(Review).where(Review.id == review.id).options(*review_options()))
    assert created is not None
    return to_read(created)


async def load_booking(session: AsyncSession, booking_id: int) -> Booking | None:
    return await session.scalar(
        select(Booking).where(Booking.id == booking_id).options(selectinload(Booking.equipment))
    )


@router.post("/bookings/{booking_id}/review", response_model=ReviewRead, status_code=status.HTTP_201_CREATED)
async def review_owner(booking_id: int, data: ReviewCreate, session: SessionDep, user: CurrentUser) -> ReviewRead:
    """Арендатор оценивает владельца"""
    booking = await load_booking(session, booking_id)
    if booking is None or booking.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Бронь не найдена")
    return await add_review(session, booking, ReviewDirection.about_owner, user, data)


@router.post("/bookings/{booking_id}/renter-review", response_model=ReviewRead, status_code=status.HTTP_201_CREATED)
async def review_renter(booking_id: int, data: ReviewCreate, session: SessionDep, user: OwnerUser) -> ReviewRead:
    """Владелец оценивает арендатора"""
    booking = await load_booking(session, booking_id)
    if booking is None or (booking.equipment.owner_id != user.id and user.role != UserRole.admin):
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Бронь не найдена")
    return await add_review(session, booking, ReviewDirection.about_renter, user, data)


async def reviews_about(session: AsyncSession, user_id: int, direction: ReviewDirection, limit: int) -> UserReviews:
    if await session.get(User, user_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Пользователь не найден")
    rating, count = await user_rating(session, user_id, direction)
    rows = await session.scalars(
        select(Review)
        .where(Review.subject_id == user_id, Review.direction == direction)
        .options(*review_options())
        .order_by(Review.created_at.desc())
        .limit(limit)
    )
    return UserReviews(rating=rating, count=count, items=[to_read(r) for r in rows])


@router.get("/owners/{owner_id}/reviews", response_model=UserReviews)
async def owner_reviews(
    owner_id: int, session: SessionDep, limit: int = Query(default=20, ge=1, le=100)
) -> UserReviews:
    """Публично: отзывы о владельце видят все, кто выбирает технику"""
    return await reviews_about(session, owner_id, ReviewDirection.about_owner, limit)


@router.get("/renters/{renter_id}/reviews", response_model=UserReviews)
async def renter_reviews(
    renter_id: int, session: SessionDep, _: OwnerUser, limit: int = Query(default=20, ge=1, le=100)
) -> UserReviews:
    """Только владельцам: отзывы об арендаторе помогают решить, подтверждать ли заявку"""
    return await reviews_about(session, renter_id, ReviewDirection.about_renter, limit)


@router.get("/my/ratings", response_model=MyRatings)
async def my_ratings(session: SessionDep, user: CurrentUser) -> MyRatings:
    owner = await user_rating(session, user.id, ReviewDirection.about_owner)
    renter = await user_rating(session, user.id, ReviewDirection.about_renter)
    return MyRatings(
        as_owner=UserReviewsSummary(rating=owner[0], count=owner[1]),
        as_renter=UserReviewsSummary(rating=renter[0], count=renter[1]),
    )
