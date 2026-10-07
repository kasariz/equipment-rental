import secrets
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.api.deps import CurrentUser, SessionDep
from app.services.telegram import client
from app.services.telegram.bot import bot_username
from app.services.telegram.client import TelegramError

router = APIRouter(prefix="/telegram", tags=["telegram"])

LINK_TTL = timedelta(minutes=10)


class TelegramStatus(BaseModel):
    enabled: bool  # настроен ли бот на сервере
    connected: bool  # привязан ли Telegram к этому аккаунту


class TelegramLink(BaseModel):
    url: str


@router.get("/status", response_model=TelegramStatus)
async def telegram_status(user: CurrentUser) -> TelegramStatus:
    return TelegramStatus(enabled=client.enabled(), connected=user.telegram_connected)


@router.post("/link", response_model=TelegramLink)
async def create_link(user: CurrentUser, session: SessionDep) -> TelegramLink:
    """Одноразовая ссылка на бота. По ней бот узнаёт, к какому аккаунту привязать чат."""
    if not client.enabled():
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail="Telegram-уведомления не настроены на сервере")
    try:
        username = await bot_username()
    except (TelegramError, Exception):
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail="Telegram сейчас недоступен, попробуйте позже")

    # Параметр start в Telegram: до 64 символов, только латиница, цифры, _ и -
    code = secrets.token_urlsafe(24)
    user.telegram_link_code = code
    user.telegram_link_expires_at = datetime.now(UTC) + LINK_TTL
    await session.commit()
    return TelegramLink(url=f"https://t.me/{username}?start={code}")


@router.delete("/link", status_code=status.HTTP_204_NO_CONTENT)
async def remove_link(user: CurrentUser, session: SessionDep) -> None:
    user.telegram_chat_id = None
    user.telegram_link_code = None
    user.telegram_link_expires_at = None
    await session.commit()
