from typing import Annotated

from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import ACCESS_TOKEN_COOKIE, decode_access_token
from app.db.session import get_session
from app.models import User, UserRole

SessionDep = Annotated[AsyncSession, Depends(get_session)]


async def get_current_user(
    session: SessionDep,
    token: Annotated[str | None, Cookie(alias=ACCESS_TOKEN_COOKIE)] = None,
) -> User:
    user_id = decode_access_token(token) if token else None
    user = await session.get(User, user_id) if user_id else None
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Нужно войти в аккаунт")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


async def get_optional_user(
    session: SessionDep,
    token: Annotated[str | None, Cookie(alias=ACCESS_TOKEN_COOKIE)] = None,
) -> User | None:
    """Для публичных страниц, где вошедшему пользователю показываем чуть больше."""
    user_id = decode_access_token(token) if token else None
    return await session.get(User, user_id) if user_id else None


OptionalUser = Annotated[User | None, Depends(get_optional_user)]


def require_role(*roles: UserRole):
    """Пример: Depends(require_role(UserRole.owner, UserRole.admin))"""

    async def checker(user: CurrentUser) -> User:
        if user.role not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Недостаточно прав")
        return user

    return checker


OwnerUser = Annotated[User, Depends(require_role(UserRole.owner, UserRole.admin))]
