import logging

import httpx
import pytest

from app.core.config import settings
from app.models import User
from app.services import alerts
from app.services.telegram import bot, client, notifications


async def test_short_outage_is_quiet_long_outage_alerts(caplog: pytest.LogCaptureFixture, monkeypatch):
    sent: list[str] = []

    async def fake_alert(text: str, key: str | None = None) -> bool:
        sent.append(text)
        return True

    monkeypatch.setattr(alerts, "send_alert", fake_alert)
    watch = bot.ConnectionWatch()
    caplog.set_level(logging.WARNING, logger=bot.log.name)

    pauses = [watch.failed(httpx.ConnectError("нет сети")) for _ in range(9)]
    assert not [r for r in caplog.records if r.levelno >= logging.ERROR]  # 9 обрывов подряд — без тревоги
    assert pauses[:5] == [5, 10, 20, 40, 60] and max(pauses) == 60  # пауза растёт, но не больше минуты

    watch.failed(httpx.ConnectError("нет сети"))
    assert [r for r in caplog.records if r.levelno >= logging.ERROR]  # ~6 минут без связи — тревога

    await watch.succeeded()
    assert sent == ["🟢 Связь с Telegram восстановлена"]
    await watch.succeeded()
    assert len(sent) == 1  # «восстановлена» — один раз, а не на каждый успешный запрос


async def test_quick_recovery_sends_nothing(monkeypatch):
    sent: list[str] = []

    async def fake_alert(text: str, key: str | None = None) -> bool:
        sent.append(text)
        return True

    monkeypatch.setattr(alerts, "send_alert", fake_alert)
    watch = bot.ConnectionWatch()
    watch.failed(httpx.ConnectError("мигнул интернет"))
    await watch.succeeded()
    assert sent == []


@pytest.fixture
def flaky_telegram(monkeypatch: pytest.MonkeyPatch):
    """Telegram, который первые N запросов не отвечает"""
    state = {"fail_times": 0, "calls": 0, "sent": 0}

    async def fake_call(method: str, params: dict | None = None, **_) -> dict:
        state["calls"] += 1
        if state["calls"] <= state["fail_times"]:
            raise httpx.ConnectError("нет сети")
        state["sent"] += 1
        return {}

    async def no_sleep(_: float) -> None:
        return None

    monkeypatch.setattr(settings, "telegram_bot_token", "test")
    monkeypatch.setattr(client, "call", fake_call)
    monkeypatch.setattr(notifications.asyncio, "sleep", no_sleep)
    return state


async def test_notification_survives_short_outage(flaky_telegram: dict, caplog):
    flaky_telegram["fail_times"] = 2
    await notifications.send(User(id=1, telegram_chat_id=555), "Новая заявка")
    assert flaky_telegram["sent"] == 1  # третья попытка прошла
    assert not [r for r in caplog.records if r.levelno >= logging.ERROR]


async def test_undelivered_notification_alerts_admin(flaky_telegram: dict, caplog):
    flaky_telegram["fail_times"] = 99
    await notifications.send(User(id=1, telegram_chat_id=555), "Новая заявка")  # исключение не вылетает наружу
    assert flaky_telegram["calls"] == 3 and flaky_telegram["sent"] == 0
    errors = [r for r in caplog.records if r.levelno >= logging.ERROR]
    assert errors and "не доставлено" in errors[0].getMessage()
