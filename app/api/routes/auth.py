from fastapi import APIRouter, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.api.deps import CurrentUser, SessionDep
from app.core.config import settings
from app.core.security import (
    ACCESS_TOKEN_COOKIE,
    DUMMY_HASH,
    create_access_token,
    hash_password,
    verify_password,
)
from app.models import User
from app.schemas.user import UserCreate, UserLogin, UserRead

router = APIRouter(prefix="/auth", tags=["auth"])


def set_auth_cookie(response: Response, user_id: int) -> None:
    # httpOnly: JavaScript не видит токен, поэтому XSS не сможет его украсть.
    # SameSite=Lax: браузер не отправит cookie в POST-запросах с чужих сайтов (защита от CSRF).
    response.set_cookie(
        key=ACCESS_TOKEN_COOKIE,
        value=create_access_token(user_id),
        max_age=settings.access_token_expire_minutes * 60,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
    )


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register(data: UserCreate, session: SessionDep, response: Response) -> User:
    user = User(
        email=data.email,
        hashed_password=hash_password(data.password),
        full_name=data.full_name,
        phone=data.phone,
        role=data.role,
    )
    session.add(user)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT, detail="Пользователь с таким email уже зарегистрирован"
        )
    await session.refresh(user)
    set_auth_cookie(response, user.id)
    return user


@router.post("/login", response_model=UserRead)
async def login(data: UserLogin, session: SessionDep, response: Response) -> User:
    user = await session.scalar(select(User).where(User.email == data.email))
    if user is None:
        verify_password(data.password, DUMMY_HASH)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Неверный email или пароль")
    if not verify_password(data.password, user.hashed_password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Неверный email или пароль")
    set_auth_cookie(response, user.id)
    return user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(response: Response) -> None:
    response.delete_cookie(ACCESS_TOKEN_COOKIE, path="/")


@router.get("/me", response_model=UserRead)
async def me(user: CurrentUser) -> User:
    return user
