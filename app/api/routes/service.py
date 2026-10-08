from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import text

from app.api.deps import SessionDep
from app.core.config import settings

router = APIRouter(tags=["service"])


@router.get("/health")
async def health(session: SessionDep) -> dict[str, str]:
    await session.execute(text("SELECT 1"))
    return {"status": "ok", "database": "ok"}


class SiteInfo(BaseModel):
    operator_name: str
    operator_email: str
    password_reset_by_email: bool
    privacy_consent_required: bool


@router.get("/site-info", response_model=SiteInfo)
async def site_info() -> SiteInfo:
    """Сведения об операторе персональных данных для страницы политики и настройки сайта"""
    from app.services import mailer

    return SiteInfo(
        operator_name=settings.operator_name,
        operator_email=settings.operator_email,
        password_reset_by_email=mailer.enabled(),
        privacy_consent_required=settings.privacy_consent_required,
    )
