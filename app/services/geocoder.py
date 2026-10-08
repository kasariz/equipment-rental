"""Нормализованные адреса через HTTP Геокодер Яндекса.

Адрес в объявлении или заявке можно только выбрать из ответа геокодера. Чтобы это нельзя было
обойти прямым запросом к API, каждый адрес из геокодера подписывается HMAC-ключом сервера,
а при сохранении подпись проверяется.
"""

import base64
import hashlib
import hmac
from dataclasses import dataclass

import httpx

from app.core.config import settings

# Ростов-на-Дону: результаты поблизости показываются первыми, но поиск идёт по всей России
BIAS_CENTER = "39.7015,47.2357"
BIAS_SPAN = "3,3"
TOO_BROAD = {"country", "province"}  # «Россия» или «Ростовская область» — не адрес техники


class GeocoderUnavailable(Exception):
    pass


@dataclass(frozen=True)
class GeoResult:
    address: str
    lat: float
    lon: float
    kind: str

    @property
    def token(self) -> str:
        return sign(self.address)


def enabled() -> bool:
    return bool(settings.yandex_geocoder_api_key)


def sign(address: str) -> str:
    digest = hmac.new(settings.secret_key.encode(), f"geo:{address}".encode(), hashlib.sha256).digest()
    return base64.urlsafe_b64encode(digest)[:32].decode()


def verify(address: str, token: str | None) -> bool:
    return token is not None and hmac.compare_digest(sign(address), token)


def parse(data: dict) -> list[GeoResult]:
    results: list[GeoResult] = []
    for member in data["response"]["GeoObjectCollection"]["featureMember"]:
        obj = member["GeoObject"]
        meta = obj["metaDataProperty"]["GeocoderMetaData"]
        address = meta.get("Address", {})
        if address.get("country_code") != "RU" or meta.get("kind") in TOO_BROAD:
            continue
        lon, lat = (float(x) for x in obj["Point"]["pos"].split())
        results.append(GeoResult(address=address.get("formatted") or meta["text"], lat=lat, lon=lon, kind=meta["kind"]))
    return results


async def _request(params: dict) -> list[GeoResult]:
    query = {"apikey": settings.yandex_geocoder_api_key, "format": "json", "lang": "ru_RU"} | params
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.get(settings.yandex_geocoder_url, params=query)
        response.raise_for_status()
        return parse(response.json())
    except (httpx.HTTPError, KeyError, ValueError) as e:
        raise GeocoderUnavailable(str(e)) from e


async def search(text: str) -> list[GeoResult]:
    return await _request({"geocode": text, "results": 7, "ll": BIAS_CENTER, "spn": BIAS_SPAN})


async def reverse(lat: float, lon: float) -> GeoResult | None:
    results = await _request({"geocode": f"{lon},{lat}", "results": 1})
    return results[0] if results else None
