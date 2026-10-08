from typing import Annotated

from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import ACCESS_TOKEN_COOKIE, decode_access_token, token_still_valid
from app.db.session import get_session
from app.models import User, UserRole

SessionDep = Annotated[AsyncSession, Depends(get_session)]


async def user_from_token(session: AsyncSession, token: str | None) -> User | None:
    decoded = decode_access_token(token) if token else None
    if decoded is None:
        return None
    user_id, stamp = decoded
    user = await session.get(User, user_id)
    if user is None or not token_still_valid(stamp, user.password_changed_at):
        return None
    return user


async def get_current_user(
    session: SessionDep,
    token: Annotated[str | None, Cookie(alias=ACCESS_TOKEN_COOKIE)] = None,
) -> User:
    user = await user_from_token(session, token)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Нужно войти в аккаунт")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


async def get_optional_user(
    session: SessionDep,
    token: Annotated[str | None, Cookie(alias=ACCESS_TOKEN_COOKIE)] = None,
) -> User | None:
    """Для публичных страниц, где вошедшему пользователю показываем чуть больше."""
    return await user_from_token(session, token)


OptionalUser = Annotated[User | None, Depends(get_optional_user)]


def require_role(*roles: UserRole):
    """Пример: Depends(require_role(UserRole.owner, UserRole.admin))"""

    async def checker(user: CurrentUser) -> User:
        if user.role not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Недостаточно прав")
        return user

    return checker


OwnerUser = Annotated[User, Depends(require_role(UserRole.owner, UserRole.admin))]
AdminUser = Annotated[User, Depends(require_role(UserRole.admin))]
