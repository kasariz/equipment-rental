import asyncio

import httpx
from sqlalchemy import text

from app.db.session import SessionLocal
from app.services.booking_expiry import expire_stale_bookings
from tests.conftest import ClientFactory, at, booking_body


async def test_quote(anon: httpx.AsyncClient, equipment: dict):
    body = booking_body(equipment["id"], at(3, 9), quantity=5, with_operator=True)
    q = (await anon.post("/api/bookings/quote", json=body)).json()
    assert (q["rental_price"], q["operator_price"], q["total_price"]) == (12500, 3000, 15500)
    assert q["available"] is True


async def test_overlapping_booking_is_rejected_but_back_to_back_is_fine(
    renter: httpx.AsyncClient, make_client: ClientFactory, equipment: dict
):
    other = await make_client("other@test.ru")
    eid = equipment["id"]
    assert (await renter.post("/api/bookings", json=booking_body(eid, at(3, 9)))).status_code == 201
    # 11:00–15:00 пересекается с 09:00–13:00
    r = await other.post("/api/bookings", json=booking_body(eid, at(3, 11)))
    assert r.status_code == 409
    assert "занято" in r.json()["detail"]
    # 13:00–17:00 начинается ровно в момент окончания: интервалы полуоткрытые
    assert (await other.post("/api/bookings", json=booking_body(eid, at(3, 13)))).status_code == 201


async def test_simultaneous_bookings_one_wins(make_client: ClientFactory, equipment: dict):
    """Два клиента жмут «Забронировать» одновременно. Проверка в базе пропускает ровно одного"""
    clients = [await make_client(f"c{i}@test.ru") for i in range(5)]
    responses = await asyncio.gather(
        *(c.post("/api/bookings", json=booking_body(equipment["id"], at(3, 9 + i))) for i, c in enumerate(clients))
    )
    codes = sorted(r.status_code for r in responses)
    # 09–13, 10–14, 11–15, 12–16, 13–17: пересекаются все, кроме пары 09–13 и 13–17
    assert codes.count(201) in (1, 2)
    assert codes.count(409) == 5 - codes.count(201)


async def test_lead_time_and_own_equipment(owner: httpx.AsyncClient, renter: httpx.AsyncClient, equipment: dict):
    from datetime import datetime, timedelta

    soon = (datetime.now().astimezone() + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
    r = await renter.post("/api/bookings", json=booking_body(equipment["id"], soon.isoformat()))
    assert r.status_code == 422
    r = await owner.post("/api/bookings", json=booking_body(equipment["id"], at(3, 9)))
    assert r.status_code == 422
    assert "собственную" in r.json()["detail"]


async def test_phone_is_saved_to_profile(renter: httpx.AsyncClient, equipment: dict):
    await renter.post("/api/bookings", json=booking_body(equipment["id"], at(3, 9), contact_phone="+7 999 000-11-22"))
    assert (await renter.get("/api/auth/me")).json()["phone"] == "+7 999 000-11-22"


async def test_lifecycle(owner: httpx.AsyncClient, renter: httpx.AsyncClient, equipment: dict):
    bid = (await renter.post("/api/bookings", json=booking_body(equipment["id"], at(3, 9)))).json()["id"]

    mine = (await renter.get("/api/my/bookings")).json()[0]
    assert mine["status"] == "pending" and mine["owner"] is None  # телефон владельца до подтверждения не видно

    incoming = (await owner.get("/api/owner/bookings", params={"status": "pending"})).json()
    assert incoming[0]["client"] == {"full_name": "Анна Клиентова", "phone": "+7 900 111-22-33"}

    assert (await renter.post(f"/api/bookings/{bid}/confirm")).status_code == 403  # клиент сам себе не подтвердит
    assert (await owner.post(f"/api/bookings/{bid}/start")).status_code == 409  # нельзя начать до подтверждения
    assert (await owner.post(f"/api/bookings/{bid}/confirm")).json()["status"] == "confirmed"
    assert (await owner.post(f"/api/bookings/{bid}/confirm")).status_code == 409

    mine = (await renter.get("/api/my/bookings")).json()[0]
    assert mine["owner"]["full_name"] == "Пётр Владелец"

    assert (await owner.post(f"/api/bookings/{bid}/start")).json()["status"] == "active"
    assert (await owner.post(f"/api/bookings/{bid}/complete")).json()["status"] == "completed"


async def test_cancel_frees_the_slot(renter: httpx.AsyncClient, make_client: ClientFactory, equipment: dict):
    other = await make_client("other@test.ru")
    bid = (await renter.post("/api/bookings", json=booking_body(equipment["id"], at(3, 9)))).json()["id"]
    assert (await other.post(f"/api/bookings/{bid}/cancel")).status_code == 404  # чужую бронь не видно
    assert (await renter.post(f"/api/bookings/{bid}/cancel")).json()["status"] == "cancelled"
    assert (await other.post("/api/bookings", json=booking_body(equipment["id"], at(3, 9)))).status_code == 201


async def test_double_confirm_at_the_same_time(owner: httpx.AsyncClient, renter: httpx.AsyncClient, equipment: dict):
    """Владелец дважды нажал «Подтвердить» (или открыл заявки на двух устройствах).
    SELECT … FOR UPDATE выстраивает запросы в очередь: второй видит уже новый статус"""
    bid = (await renter.post("/api/bookings", json=booking_body(equipment["id"], at(3, 9)))).json()["id"]
    first, second = await asyncio.gather(
        owner.post(f"/api/bookings/{bid}/confirm"), owner.post(f"/api/bookings/{bid}/confirm")
    )
    assert sorted([first.status_code, second.status_code]) == [200, 409]


async def test_cancel_and_confirm_at_the_same_time_end_cancelled(
    owner: httpx.AsyncClient, renter: httpx.AsyncClient, equipment: dict
):
    """Порядок может быть любым, но итог один: клиент отменил — бронь отменена"""
    bid = (await renter.post("/api/bookings", json=booking_body(equipment["id"], at(3, 9)))).json()["id"]
    cancel, _ = await asyncio.gather(
        renter.post(f"/api/bookings/{bid}/cancel"), owner.post(f"/api/bookings/{bid}/confirm")
    )
    assert cancel.status_code == 200
    assert (await renter.get("/api/my/bookings")).json()[0]["status"] == "cancelled"


async def test_busy_intervals_and_availability_filter(
    renter: httpx.AsyncClient, anon: httpx.AsyncClient, equipment: dict
):
    await renter.post("/api/bookings", json=booking_body(equipment["id"], at(3, 9)))
    busy = (await anon.get(f"/api/equipment/{equipment['id']}/busy")).json()
    assert len(busy) == 1 and "client" not in busy[0]

    def free(start: str, end: str) -> int:
        return {"available_from": start, "available_to": end}

    r = await anon.get("/api/equipment", params=free(at(3, 10), at(3, 11)))
    assert r.json()["total"] == 0
    r = await anon.get("/api/equipment", params=free(at(3, 13), at(3, 15)))
    assert r.json()["total"] == 1


async def test_unconfirmed_booking_expires(renter: httpx.AsyncClient, anon: httpx.AsyncClient, equipment: dict):
    bid = (await renter.post("/api/bookings", json=booking_body(equipment["id"], at(3, 9)))).json()["id"]
    assert await expire_stale_bookings() == 0  # свежая заявка не сгорает

    async with SessionLocal() as session:
        await session.execute(
            text("UPDATE bookings SET created_at = now() - interval '25 hours' WHERE id = :id"), {"id": bid}
        )
        await session.commit()
    assert await expire_stale_bookings() == 1

    assert (await renter.get("/api/my/bookings")).json()[0]["status"] == "expired"
    quote = await anon.post("/api/bookings/quote", json=booking_body(equipment["id"], at(3, 9)))
    assert quote.json()["available"] is True
