from datetime import UTC, datetime

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUser, SessionDep
from app.core.config import settings
from app.core.ratelimit import client_ip, limiter
from app.core.security import (
    ACCESS_TOKEN_COOKIE,
    DUMMY_HASH,
    create_access_token,
    hash_password,
    verify_password,
)
from app.models import Equipment, User
from app.schemas.user import (
    AccountDelete,
    PasswordResetConfirm,
    PasswordResetRequest,
    UserCreate,
    UserLogin,
    UserRead,
)
from app.services import password_reset
from app.services.media import delete_equipment_photo_file

router = APIRouter(prefix="/auth", tags=["auth"])


def set_auth_cookie(response: Response, user: User) -> None:
    # httpOnly: JavaScript не видит токен, поэтому XSS не сможет его украсть.
    # SameSite=Lax: браузер не отправит cookie в POST-запросах с чужих сайтов (защита от CSRF).
    response.set_cookie(
        key=ACCESS_TOKEN_COOKIE,
        value=create_access_token(user.id, user.password_changed_at),
        max_age=settings.access_token_expire_minutes * 60,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
    )


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register(data: UserCreate, session: SessionDep, response: Response, request: Request) -> User:
    limiter.hit(f"register:{client_ip(request)}", limit=5, window_seconds=3600)
    if settings.privacy_consent_required and not data.consent:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Нужно согласие на обработку персональных данных"
        )
    user = User(
        email=data.email,
        hashed_password=hash_password(data.password),
        full_name=data.full_name,
        phone=data.phone,
        role=data.role,
        consent_at=datetime.now(UTC) if data.consent else None,
    )
    session.add(user)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Пользователь с таким email уже зарегистрирован") from None
    await session.refresh(user)
    set_auth_cookie(response, user)
    return user


@router.post("/login", response_model=UserRead)
async def login(data: UserLogin, session: SessionDep, response: Response, request: Request) -> User:
    # Два ограничения: с одного адреса и на один аккаунт — второе мешает перебору пароля
    # к конкретному email с множества адресов
    limiter.hit(f"login-ip:{client_ip(request)}", limit=20, window_seconds=600)
    limiter.hit(f"login-email:{data.email}", limit=8, window_seconds=900)
    user = await session.scalar(select(User).where(User.email == data.email))
    if user is None:
        verify_password(data.password, DUMMY_HASH)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Неверный email или пароль")
    if not verify_password(data.password, user.hashed_password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Неверный email или пароль")
    set_auth_cookie(response, user)
    return user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(response: Response) -> None:
    response.delete_cookie(ACCESS_TOKEN_COOKIE, path="/")


@router.get("/me", response_model=UserRead)
async def me(user: CurrentUser) -> User:
    return user


@router.post("/password-reset/request", status_code=status.HTTP_202_ACCEPTED)
async def request_password_reset(
    data: PasswordResetRequest, session: SessionDep, request: Request, background: BackgroundTasks
) -> dict[str, str]:
    """Ответ одинаковый, есть такой email или нет: иначе по нему можно проверять, кто зарегистрирован"""
    limiter.hit(f"reset-ip:{client_ip(request)}", limit=10, window_seconds=3600)
    limiter.hit(f"reset-email:{data.email.lower()}", limit=3, window_seconds=3600)
    user = await session.scalar(select(User).where(User.email == data.email.lower()))
    if user is not None:
        link = password_reset.issue_code(user)
        await session.commit()
        background.add_task(password_reset.deliver, user, link)
    return {"detail": "Если такой аккаунт есть, мы отправили ссылку для смены пароля"}


@router.post("/password-reset/confirm", status_code=status.HTTP_204_NO_CONTENT)
async def confirm_password_reset(data: PasswordResetConfirm, session: SessionDep, request: Request) -> None:
    limiter.hit(f"reset-confirm:{client_ip(request)}", limit=10, window_seconds=600)
    user = await session.scalar(select(User).where(User.password_reset_hash == password_reset.hash_code(data.token)))
    expires = user.password_reset_expires_at if user else None
    if user is None or expires is None or expires < datetime.now(UTC):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Ссылка недействительна или устарела. Запросите новую")
    user.hashed_password = hash_password(data.password)
    user.password_reset_hash = None
    user.password_reset_expires_at = None
    user.password_changed_at = datetime.now(UTC)  # все старые входы на других устройствах перестают действовать
    await session.commit()


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(data: AccountDelete, session: SessionDep, user: CurrentUser, response: Response) -> None:
    """Отзыв согласия на обработку данных (152-ФЗ): аккаунт и всё связанное удаляется"""
    if not verify_password(data.password, user.hashed_password):
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Неверный пароль")
    files = [
        p.filename
        for eq in await session.scalars(
            select(Equipment).where(Equipment.owner_id == user.id).options(selectinload(Equipment.photos))
        )
        for p in eq.photos
    ]
    await session.delete(user)
    await session.commit()
    for name in files:
        delete_equipment_photo_file(name)
    response.delete_cookie(ACCESS_TOKEN_COOKIE, path="/")
