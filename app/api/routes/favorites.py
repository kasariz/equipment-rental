from fastapi import APIRouter, HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUser, SessionDep
from app.api.routes.equipment import to_list_item
from app.models import Equipment, Favorite, ReviewDirection
from app.schemas.equipment import EquipmentListItem
from app.services.ratings import user_ratings

router = APIRouter(tags=["favorites"])


@router.put("/favorites/{equipment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def add_favorite(equipment_id: int, session: SessionDep, user: CurrentUser) -> None:
    if await session.get(Equipment, equipment_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Техника не найдена")
    # Повторное добавление ничего не ломает: PUT идемпотентен
    await session.execute(insert(Favorite).values(user_id=user.id, equipment_id=equipment_id).on_conflict_do_nothing())
    await session.commit()


@router.delete("/favorites/{equipment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_favorite(equipment_id: int, session: SessionDep, user: CurrentUser) -> None:
    await session.execute(delete(Favorite).where(Favorite.user_id == user.id, Favorite.equipment_id == equipment_id))
    await session.commit()


@router.get("/my/favorites", response_model=list[EquipmentListItem])
async def my_favorites(session: SessionDep, user: CurrentUser) -> list[EquipmentListItem]:
    rows = list(
        await session.scalars(
            select(Equipment)
            .join(Favorite, Favorite.equipment_id == Equipment.id)
            .where(Favorite.user_id == user.id)
            .options(selectinload(Equipment.category), selectinload(Equipment.photos))
            .order_by(Favorite.created_at.desc())
        )
    )
    ratings = await user_ratings(session, [e.owner_id for e in rows], ReviewDirection.about_owner)
    items = []
    for eq in rows:
        rating, count = ratings.get(eq.owner_id, (None, 0))
        item = to_list_item(eq, rating=rating, reviews_count=count)
        item.is_favorite = True
        items.append(item)
    return items
