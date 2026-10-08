from typing import Any

import httpx
import pytest

from app.core.config import settings
from app.services import geocoder
from tests.conftest import PASSWORD, at, booking_body, create_equipment

GEOCODER_RESPONSE = {
    "response": {
        "GeoObjectCollection": {
            "featureMember": [
                {
                    "GeoObject": {
                        "metaDataProperty": {
                            "GeocoderMetaData": {
                                "kind": "house",
                                "text": "Россия, Ростов-на-Дону, улица Малиновского, 25",
                                "Address": {
                                    "country_code": "RU",
                                    "formatted": "Ростов-на-Дону, улица Малиновского, 25",
                                },
                            }
                        },
                        "Point": {"pos": "39.638 47.233"},
                    }
                },
                {  # область целиком — слишком широко для адреса техники
                    "GeoObject": {
                        "metaDataProperty": {
                            "GeocoderMetaData": {
                                "kind": "province",
                                "text": "Россия, Ростовская область",
                                "Address": {"country_code": "RU", "formatted": "Ростовская область"},
                            }
                        },
                        "Point": {"pos": "40.5 47.5"},
                    }
                },
                {  # не Россия
                    "GeoObject": {
                        "metaDataProperty": {
                            "GeocoderMetaData": {
                                "kind": "locality",
                                "text": "Казахстан, Астана",
                                "Address": {"country_code": "KZ", "formatted": "Астана"},
                            }
                        },
                        "Point": {"pos": "71.4 51.1"},
                    }
                },
            ]
        }
    }
}


@pytest.fixture
def fake_geocoder(monkeypatch: pytest.MonkeyPatch) -> list[dict]:
    requests: list[dict] = []

    async def fake_request(params: dict[str, Any]):
        requests.append(params)
        return geocoder.parse(GEOCODER_RESPONSE)

    monkeypatch.setattr(settings, "yandex_geocoder_api_key", "test-key")
    monkeypatch.setattr(geocoder, "_request", fake_request)
    return requests


async def test_registration_normalizes_phone(anon: httpx.AsyncClient):
    r = await anon.post(
        "/api/auth/register",
        json={"email": "p@test.ru", "password": PASSWORD, "full_name": "Павел", "phone": "8 (900) 123-45-67"},
    )
    assert r.json()["phone"] == "+79001234567"


@pytest.mark.parametrize("phone", ["12345", "+1 212 555 0100", "8 900 123 45 6"])
async def test_registration_rejects_bad_phone(anon: httpx.AsyncClient, phone: str):
    r = await anon.post(
        "/api/auth/register",
        json={"email": "p@test.ru", "password": PASSWORD, "full_name": "Павел", "phone": phone},
    )
    assert r.status_code == 422


async def test_geocoder_suggestions_are_russian_and_specific(fake_geocoder: list, owner: httpx.AsyncClient):
    r = await owner.get("/api/geo/search", params={"q": "Малиновского 25"})
    assert [s["address"] for s in r.json()] == ["Ростов-на-Дону, улица Малиновского, 25"]
    assert r.json()[0]["lat"] == 47.233 and r.json()[0]["lon"] == 39.638


async def test_geocoder_requires_login(fake_geocoder: list, anon: httpx.AsyncClient):
    assert (await anon.get("/api/geo/search", params={"q": "Малиновского"})).status_code == 401


async def test_address_must_come_from_geocoder(fake_geocoder: list, owner: httpx.AsyncClient):
    suggestion = (await owner.get("/api/geo/search", params={"q": "Малиновского"})).json()[0]

    r = await owner.post("/api/equipment", json=await body(owner, address="Деревня Простоквашино"))
    assert r.status_code == 422 and "подсказок" in r.text

    forged = await body(owner, address="Деревня Простоквашино", address_token=suggestion["token"])
    assert (await owner.post("/api/equipment", json=forged)).status_code == 422  # чужая подпись не подходит

    ok = await body(owner, address=suggestion["address"], address_token=suggestion["token"])
    assert (await owner.post("/api/equipment", json=ok)).status_code == 201


async def test_delivery_address_must_come_from_geocoder(
    fake_geocoder: list, owner: httpx.AsyncClient, renter: httpx.AsyncClient
):
    suggestion = (await owner.get("/api/geo/search", params={"q": "Малиновского"})).json()[0]
    eq = await create_equipment(owner, address=suggestion["address"], address_token=suggestion["token"])
    bad = booking_body(eq["id"], at(3, 9), delivery_address="куда-нибудь")
    assert (await renter.post("/api/bookings", json=bad)).status_code == 422
    good = booking_body(
        eq["id"], at(3, 9), delivery_address=suggestion["address"], delivery_address_token=suggestion["token"]
    )
    assert (await renter.post("/api/bookings", json=good)).status_code == 201


async def body(owner: httpx.AsyncClient, **overrides) -> dict:
    categories = (await owner.get("/api/categories")).json()
    return {
        "name": "JCB",
        "category_id": categories[0]["id"],
        "latitude": 47.23,
        "longitude": 39.64,
        "price_per_hour": 3000,
    } | overrides
