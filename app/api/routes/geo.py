from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel

from app.api.deps import CurrentUser
from app.services import geocoder
from app.services.geocoder import GeocoderUnavailable, GeoResult

router = APIRouter(prefix="/geo", tags=["geo"])


class GeoStatus(BaseModel):
    enabled: bool


class GeoSuggestion(BaseModel):
    address: str
    lat: float
    lon: float
    token: str  # подпись сервера: без неё адрес не примут при сохранении


def to_suggestion(r: GeoResult) -> GeoSuggestion:
    return GeoSuggestion(address=r.address, lat=r.lat, lon=r.lon, token=r.token)


def unavailable() -> HTTPException:
    return HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail="Поиск адресов временно недоступен")


@router.get("/status", response_model=GeoStatus)
async def geo_status() -> GeoStatus:
    return GeoStatus(enabled=geocoder.enabled())


# Только для вошедших: у геокодера дневной лимит запросов, анонимы его быстро съедят
@router.get("/search", response_model=list[GeoSuggestion])
async def geo_search(_: CurrentUser, q: str = Query(min_length=3, max_length=200)) -> list[GeoSuggestion]:
    if not geocoder.enabled():
        raise unavailable()
    try:
        return [to_suggestion(r) for r in await geocoder.search(q)]
    except GeocoderUnavailable as e:
        raise unavailable() from e


@router.get("/reverse", response_model=GeoSuggestion | None)
async def geo_reverse(
    _: CurrentUser, lat: float = Query(ge=-90, le=90), lon: float = Query(ge=-180, le=180)
) -> GeoSuggestion | None:
    if not geocoder.enabled():
        raise unavailable()
    try:
        result = await geocoder.reverse(lat, lon)
    except GeocoderUnavailable as e:
        raise unavailable() from e
    return to_suggestion(result) if result else None


def ensure_normalized(address: str | None, token: str | None) -> None:
    """Адрес должен прийти из геокодера. Если геокодер не настроен, принимаем как есть"""
    if address and geocoder.enabled() and not geocoder.verify(address, token):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Выберите адрес из подсказок, а не вводите вручную"
        )
