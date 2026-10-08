"""Демо-набор для показа заказчику не должен ломаться при изменениях моделей и ограничений базы"""

import httpx

from app.db.session import SessionLocal
from app.scripts.demo import DEFAULT_PASSWORD, OWNER_EMAIL, RENTER_EMAIL, create_demo, remove_demo


async def test_demo_data_covers_all_scenarios(anon: httpx.AsyncClient, make_client):
    assert await create_demo() == {"owner": OWNER_EMAIL, "renter": RENTER_EMAIL, "password": DEFAULT_PASSWORD}
    assert await create_demo() == {}  # повторный запуск ничего не дублирует

    owner, renter = await make_client(), await make_client()
    for c, email in ((owner, OWNER_EMAIL), (renter, RENTER_EMAIL)):
        assert (await c.post("/api/auth/login", json={"email": email, "password": DEFAULT_PASSWORD})).status_code == 200

    statuses = {b["status"] for b in (await owner.get("/api/owner/bookings")).json()}
    assert statuses == {"pending", "confirmed", "active", "completed", "rejected", "cancelled", "expired"}
    assert {b["status"] for b in (await renter.get("/api/my/bookings")).json()} >= {"pending", "confirmed", "completed"}
    assert (await owner.get("/api/my/ratings")).json()["as_owner"]["count"] >= 3
    assert (await renter.get("/api/my/ratings")).json()["as_renter"]["count"] >= 2
    assert len((await renter.get("/api/my/favorites")).json()) == 3

    # Сброс удаляет только демо-аккаунты
    async with SessionLocal() as session:
        assert await remove_demo(session) == 5
    assert (await anon.get("/api/equipment")).json()["total"] == 0
