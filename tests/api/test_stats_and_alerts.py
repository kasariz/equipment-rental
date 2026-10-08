import logging
from datetime import datetime, timedelta

import httpx
import pytest
from sqlalchemy import text

from app.core.config import settings
from app.db.session import SessionLocal
from app.services import alerts
from tests.conftest import MSK, at, booking_body, create_equipment


def month_of(days: int) -> str:
    return (datetime.now(MSK) + timedelta(days=days)).strftime("%Y-%m")


async def test_owner_stats(owner: httpx.AsyncClient, renter: httpx.AsyncClient, equipment: dict):
    eid = equipment["id"]
    second = await create_equipment(owner, name="Простаивает")

    # Аренда на 2 смены (2 дня), отклонённая заявка и закрытый владельцем день
    deal = (await renter.post("/api/bookings", json=booking_body(eid, at(10, 8), rate_type="shift", quantity=2))).json()
    for action in ("confirm", "start", "complete"):
        await owner.post(f"/api/bookings/{deal['id']}/{action}")
    rejected = (await renter.post("/api/bookings", json=booking_body(eid, at(15, 9)))).json()
    await owner.post(f"/api/bookings/{rejected['id']}/reject", json={})
    day = (datetime.now(MSK) + timedelta(days=20)).replace(hour=0, minute=0, second=0, microsecond=0)
    await owner.post(
        f"/api/equipment/{eid}/blocks", json={"start": day.isoformat(), "end": (day + timedelta(days=1)).isoformat()}
    )

    # Все события должны попасть в один месяц — иначе тест зависел бы от даты запуска
    months = {month_of(10), month_of(11), month_of(15), month_of(20)}
    if len(months) > 1:
        pytest.skip("События попали на разные месяцы")
    stats = (await owner.get("/api/owner/stats", params={"month": month_of(10)})).json()

    assert stats["requests"]["total"] == 2
    assert stats["requests"]["confirmed"] == 1 and stats["requests"]["rejected"] == 1
    assert stats["revenue_completed"] == deal["total_price"] and stats["revenue_expected"] == 0
    busy = {e["name"]: e for e in stats["equipment"]}
    assert busy["JCB 3CX"]["busy_days"] == 3 and busy["JCB 3CX"]["blocked_days"] == 1
    assert busy["Простаивает"]["busy_days"] == 0 and busy["Простаивает"]["utilization"] == 0
    assert len(stats["days"]) == stats["days_in_month"]
    assert sum(d["busy"] for d in stats["days"]) == 3
    assert second["id"] in {e["id"] for e in stats["equipment"]}


async def test_stats_are_owner_only(renter: httpx.AsyncClient):
    assert (await renter.get("/api/owner/stats")).status_code == 403


async def test_stats_bad_month(owner: httpx.AsyncClient):
    assert (await owner.get("/api/owner/stats", params={"month": "2026-13"})).status_code == 422


async def test_stats_ignore_other_owners(owner: httpx.AsyncClient, make_client, renter, equipment):
    other = await make_client("o2@test.ru", role="owner")
    await renter.post("/api/bookings", json=booking_body(equipment["id"], at(3, 9)))
    stats = (await other.get("/api/owner/stats")).json()
    assert stats["equipment_count"] == 0 and stats["requests"]["total"] == 0


@pytest.fixture
def alert_outbox(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    sent: list[str] = []

    class FakeResponse:
        status_code = 200

    class FakeClient:
        def __init__(self, *a, **kw): ...
        async def __aenter__(self):
            return self

        async def __aexit__(self, *a): ...
        async def post(self, url: str, json: dict):
            sent.append(json["text"])
            return FakeResponse()

    monkeypatch.setattr(settings, "alert_bot_token", "test")
    monkeypatch.setattr(settings, "alert_chat_id", "42")
    monkeypatch.setattr(alerts.httpx, "AsyncClient", FakeClient)
    alerts._last_sent.clear()
    return sent


async def test_alerts_are_throttled(alert_outbox: list[str]):
    assert await alerts.send_alert("Сломалось", key="x") is True
    assert await alerts.send_alert("Сломалось опять", key="x") is False  # тот же ключ в течение 10 минут
    assert await alerts.send_alert("Другое", key="y") is True
    assert alert_outbox == ["Сломалось", "Другое"]


async def test_error_log_goes_to_telegram(alert_outbox: list[str]):
    import asyncio

    handler = alerts.TelegramAlertHandler()
    logger = logging.getLogger("test.alerts")
    logger.addHandler(handler)
    try:
        try:
            raise ValueError("бронь без техники")
        except ValueError:
            logger.exception("Не удалось обработать заявку")
        logger.warning("это не ошибка, не присылаем")
        await asyncio.sleep(0.05)
    finally:
        logger.removeHandler(handler)
    assert len(alert_outbox) == 1
    assert "Не удалось обработать заявку" in alert_outbox[0] and "ValueError: бронь без техники" in alert_outbox[0]


async def test_alerts_disabled_without_token(db):
    async with SessionLocal() as session:  # фикстура db нужна только ради чистой базы
        await session.execute(text("SELECT 1"))
    assert alerts.enabled() is False
    assert await alerts.send_alert("тишина") is False
