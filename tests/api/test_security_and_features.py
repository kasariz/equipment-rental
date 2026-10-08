from datetime import timedelta

import httpx
import pytest

from app.core.config import settings
from app.core.ratelimit import limiter
from app.services import mailer, password_reset
from tests.conftest import MSK, PASSWORD, ClientFactory, at, booking_body, create_equipment


@pytest.fixture
def rate_limits(monkeypatch: pytest.MonkeyPatch):
    limiter.reset()
    monkeypatch.setattr(settings, "rate_limit_enabled", True)
    yield
    limiter.reset()


# ---------- 152-ФЗ и аккаунт ----------


async def test_registration_requires_consent(anon: httpx.AsyncClient):
    body = {"email": "a@test.ru", "password": PASSWORD, "full_name": "Анна"}
    assert (await anon.post("/api/auth/register", json=body)).status_code == 422
    assert (await anon.post("/api/auth/register", json=body | {"consent": False})).status_code == 422
    assert (await anon.post("/api/auth/register", json=body | {"consent": True})).status_code == 201


async def test_delete_own_account(owner: httpx.AsyncClient, renter: httpx.AsyncClient, anon, equipment: dict):
    assert (await owner.request("DELETE", "/api/auth/me", json={"password": "wrong-one"})).status_code == 403
    assert (await owner.request("DELETE", "/api/auth/me", json={"password": PASSWORD})).status_code == 204
    assert (await owner.get("/api/auth/me")).status_code == 401
    assert (await anon.get("/api/equipment")).json()["total"] == 0  # техника ушла вместе с аккаунтом


# ---------- ограничение частоты ----------


async def test_login_is_rate_limited_per_account(rate_limits, renter: httpx.AsyncClient, make_client: ClientFactory):
    attacker = await make_client()
    for _ in range(8):
        r = await attacker.post("/api/auth/login", json={"email": "client@test.ru", "password": "guess-guess"})
        assert r.status_code == 401
    r = await attacker.post("/api/auth/login", json={"email": "client@test.ru", "password": PASSWORD})
    assert r.status_code == 429  # даже верный пароль: лимит на аккаунт исчерпан
    assert "Retry-After" in r.headers and "Попробуйте через" in r.json()["detail"]


async def test_registration_is_rate_limited(rate_limits, anon: httpx.AsyncClient):
    codes = [
        (
            await anon.post(
                "/api/auth/register",
                json={"email": f"bot{i}@test.ru", "password": PASSWORD, "full_name": "Бот", "consent": True},
            )
        ).status_code
        for i in range(6)
    ]
    assert codes == [201] * 5 + [429]


# ---------- восстановление пароля ----------


@pytest.fixture
def outbox(monkeypatch: pytest.MonkeyPatch) -> list[dict]:
    sent: list[dict] = []

    async def fake_send(to: str, subject: str, text: str) -> bool:
        sent.append({"to": to, "subject": subject, "text": text})
        return True

    monkeypatch.setattr(mailer, "send", fake_send)
    return sent


def link_token(text: str) -> str:
    return text.split("reset-password?token=")[1].split()[0]


async def test_password_reset_flow(outbox: list, renter: httpx.AsyncClient, make_client: ClientFactory):
    other_device = await make_client()
    await other_device.post("/api/auth/login", json={"email": "client@test.ru", "password": PASSWORD})

    anon = await make_client()
    r = await anon.post("/api/auth/password-reset/request", json={"email": "Client@Test.ru"})
    assert r.status_code == 202
    unknown = await anon.post("/api/auth/password-reset/request", json={"email": "nobody@test.ru"})
    assert unknown.json() == r.json()  # по ответу не понять, есть ли такой email
    assert len(outbox) == 1 and outbox[0]["to"] == "client@test.ru"

    token = link_token(outbox[0]["text"])
    assert (
        await anon.post("/api/auth/password-reset/confirm", json={"token": token, "password": "new-pass-123"})
    ).status_code == 204
    # Ссылка одноразовая
    again = await anon.post("/api/auth/password-reset/confirm", json={"token": token, "password": "other-pass-1"})
    assert again.status_code == 400

    # Старые входы погашены на всех устройствах, новый пароль работает
    assert (await renter.get("/api/auth/me")).status_code == 401
    assert (await other_device.get("/api/auth/me")).status_code == 401
    login = await anon.post("/api/auth/login", json={"email": "client@test.ru", "password": "new-pass-123"})
    assert login.status_code == 200
    assert (await anon.get("/api/auth/me")).status_code == 200


async def test_expired_reset_link(outbox: list, renter: httpx.AsyncClient, anon: httpx.AsyncClient, monkeypatch):
    monkeypatch.setattr(settings, "password_reset_ttl_minutes", -1)
    await anon.post("/api/auth/password-reset/request", json={"email": "client@test.ru"})
    token = link_token(outbox[0]["text"])
    r = await anon.post("/api/auth/password-reset/confirm", json={"token": token, "password": "new-pass-123"})
    assert r.status_code == 400


async def test_admin_can_issue_reset_link(make_client: ClientFactory, renter: httpx.AsyncClient):
    from sqlalchemy import update

    from app.db.session import SessionLocal
    from app.models import User, UserRole

    admin = await make_client("admin@test.ru")
    async with SessionLocal() as session:
        await session.execute(update(User).where(User.email == "admin@test.ru").values(role=UserRole.admin))
        await session.commit()
    rid = (await renter.get("/api/auth/me")).json()["id"]
    url = (await admin.post(f"/api/admin/users/{rid}/reset-link")).json()["url"]
    assert "/reset-password?token=" in url
    assert (await renter.post(f"/api/admin/users/{rid}/reset-link")).status_code == 403
    token = url.split("token=")[1]
    assert password_reset.hash_code(token)  # код в базе хранится только хэшем


# ---------- календарь владельца ----------


def day(days: int) -> str:
    from datetime import datetime

    d = (datetime.now(MSK) + timedelta(days=days)).replace(hour=0, minute=0, second=0, microsecond=0)
    return d.isoformat()


async def test_owner_blocks_days(owner: httpx.AsyncClient, renter: httpx.AsyncClient, anon, equipment: dict):
    eid = equipment["id"]
    r = await owner.post(f"/api/equipment/{eid}/blocks", json={"start": day(3), "end": day(5), "reason": "ТО"})
    assert r.status_code == 201
    block_id = r.json()["id"]

    # Клиент не может забронировать закрытые дни, они видны как занятые
    assert (await renter.post("/api/bookings", json=booking_body(eid, at(4, 9)))).status_code == 409
    assert len((await anon.get(f"/api/equipment/{eid}/busy")).json()) == 1
    free = await anon.get("/api/equipment", params={"available_from": at(3, 10), "available_to": at(3, 12)})
    assert free.json()["total"] == 0

    # Закрытие не появляется ни в заявках владельца, ни в его бронях
    assert (await owner.get("/api/owner/bookings")).json() == []
    assert (await owner.get("/api/my/bookings")).json() == []
    calendar = (await owner.get(f"/api/equipment/{eid}/calendar", params={"from": day(0), "to": day(30)})).json()
    assert calendar[0]["kind"] == "block" and calendar[0]["reason"] == "ТО"

    # Поверх брони закрыть нельзя
    await renter.post("/api/bookings", json=booking_body(eid, at(7, 9)))
    clash = await owner.post(f"/api/equipment/{eid}/blocks", json={"start": day(7), "end": day(8)})
    assert clash.status_code == 409

    # Открыли дни — снова можно бронировать
    assert (await owner.delete(f"/api/equipment/{eid}/blocks/{block_id}")).status_code == 204
    assert (await renter.post("/api/bookings", json=booking_body(eid, at(4, 9)))).status_code == 201


async def test_only_owner_manages_blocks(make_client: ClientFactory, renter: httpx.AsyncClient, equipment: dict):
    stranger = await make_client("o2@test.ru", role="owner")
    body = {"start": day(3), "end": day(4)}
    assert (await stranger.post(f"/api/equipment/{equipment['id']}/blocks", json=body)).status_code == 403
    assert (await renter.post(f"/api/equipment/{equipment['id']}/blocks", json=body)).status_code == 403


async def test_owner_can_delete_equipment_with_only_own_blocks(owner: httpx.AsyncClient, equipment: dict):
    await owner.post(f"/api/equipment/{equipment['id']}/blocks", json={"start": day(3), "end": day(4)})
    assert (await owner.delete(f"/api/equipment/{equipment['id']}")).status_code == 204


# ---------- избранное, область карты, похожая техника ----------


async def test_favorites(renter: httpx.AsyncClient, anon: httpx.AsyncClient, equipment: dict):
    eid = equipment["id"]
    assert (await renter.put(f"/api/favorites/{eid}")).status_code == 204
    assert (await renter.put(f"/api/favorites/{eid}")).status_code == 204  # повтор не ломает
    assert [i["id"] for i in (await renter.get("/api/my/favorites")).json()] == [eid]
    assert (await renter.get("/api/equipment")).json()["items"][0]["is_favorite"] is True
    assert (await renter.get(f"/api/equipment/{eid}")).json()["is_favorite"] is True
    assert (await anon.get("/api/equipment")).json()["items"][0]["is_favorite"] is False
    assert (await anon.put(f"/api/favorites/{eid}")).status_code == 401
    assert (await renter.delete(f"/api/favorites/{eid}")).status_code == 204
    assert (await renter.get("/api/my/favorites")).json() == []


async def test_search_in_map_area(owner: httpx.AsyncClient, anon: httpx.AsyncClient):
    await create_equipment(owner, name="В Ростове", latitude=47.23, longitude=39.70)
    await create_equipment(owner, name="В Батайске", latitude=47.14, longitude=39.74)
    box = {"min_lat": 47.2, "max_lat": 47.3, "min_lon": 39.6, "max_lon": 39.8}
    r = await anon.get("/api/equipment", params=box)
    assert [i["name"] for i in r.json()["items"]] == ["В Ростове"]
    assert (await anon.get("/api/equipment", params={"min_lat": 47.2})).status_code == 422


async def test_similar_equipment(owner: httpx.AsyncClient, anon: httpx.AsyncClient):
    categories = (await anon.get("/api/categories")).json()
    base = await create_equipment(owner, name="Базовый", latitude=47.23, longitude=39.70)
    await create_equipment(owner, name="Далёкий", latitude=47.5, longitude=40.2)
    await create_equipment(owner, name="Близкий", latitude=47.24, longitude=39.71)
    await create_equipment(owner, name="Другая категория", category_id=categories[3]["id"])
    similar = (await anon.get(f"/api/equipment/{base['id']}/similar")).json()
    assert [i["name"] for i in similar] == ["Близкий", "Далёкий"]
