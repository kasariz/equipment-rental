"""Рейтинги по отзывам: владельцев (от арендаторов) и арендаторов (от владельцев)"""

from sqlalchemy import Subquery, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Review, ReviewDirection


def ratings_subquery(direction: ReviewDirection = ReviewDirection.about_owner) -> Subquery:
    return (
        select(
            Review.subject_id.label("subject_id"),
            func.avg(Review.rating).label("rating"),
            func.count(Review.id).label("reviews_count"),
        )
        .where(Review.direction == direction)
        .group_by(Review.subject_id)
        .subquery()
    )


async def user_ratings(
    session: AsyncSession, user_ids: list[int], direction: ReviewDirection
) -> dict[int, tuple[float, int]]:
    """{id пользователя: (средняя оценка, число отзывов)} одним запросом для целого списка"""
    if not user_ids:
        return {}
    rows = await session.execute(
        select(Review.subject_id, func.avg(Review.rating), func.count(Review.id))
        .where(Review.subject_id.in_(set(user_ids)), Review.direction == direction)
        .group_by(Review.subject_id)
    )
    return {uid: (round(float(avg), 1), count) for uid, avg, count in rows}


async def user_rating(session: AsyncSession, user_id: int, direction: ReviewDirection) -> tuple[float | None, int]:
    found = await user_ratings(session, [user_id], direction)
    return found.get(user_id, (None, 0))


async def owner_rating(session: AsyncSession, owner_id: int) -> tuple[float | None, int]:
    return await user_rating(session, owner_id, ReviewDirection.about_owner)
