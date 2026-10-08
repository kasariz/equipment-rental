from typing import Any

import httpx
import pytest

from app.core.config import settings
from app.services.telegram import bot, client
from app.services.telegram.bot import handle_update
from app.services.telegram.client import TelegramError
from tests.conftest import ClientFactory, at, booking_body

BLOCKED_CHAT = 666


@pytest.fixture
def telegram(monkeypatch: pytest.MonkeyPatch) -> list[dict]:
    """Подменяем Bot API: вместо отправки складываем сообщения в список"""
    sent: list[dict] = []

    async def fake_call(method: str, params: dict[str, Any] | None = None, **_) -> Any:
        if method == "getMe":
            return {"username": "test_bot"}
        if method == "sendMessage":
            if params["chat_id"] == BLOCKED_CHAT:
                raise TelegramError(403, "Forbidden: bot was blocked by the user")
            sent.append(params)
            return {}
        raise AssertionError(f"Неожиданный вызов {method}")

    monkeypatch.setattr(settings, "telegram_bot_token", "test-token")
    monkeypatch.setattr(client, "call", fake_call)
    monkeypatch.setattr(bot, "_username", None)
    return sent


def message(chat_id: int, text: str, chat_type: str = "private") -> dict:
    return {"update_id": 1, "message": {"chat": {"id": chat_id, "type": chat_type}, "text": text}}


async def connect(c: httpx.AsyncClient, chat_id: int) -> None:
    url = (await c.post("/api/telegram/link")).json()["url"]
    assert url.startswith("https://t.me/test_bot?start=")
    await handle_update(message(chat_id, f"/start {url.split('start=')[1]}"))


async def test_link_and_unlink(telegram: list[dict], owner: httpx.AsyncClient):
    assert (await owner.get("/api/telegram/status")).json() == {"enabled": True, "connected": False}
    await connect(owner, 1001)
    assert (await owner.get("/api/telegram/status")).json()["connected"] is True
    assert telegram[-1]["text"].startswith("Готово, Пётр Владелец")

    await handle_update(message(1001, "/stop"))
    assert (await owner.get("/api/telegram/status")).json()["connected"] is False


async def test_wrong_code_and_group_chats(telegram: list[dict], owner: httpx.AsyncClient):
    await handle_update(message(1001, "/start not-a-real-code"))
    assert "устарела" in telegram[-1]["text"]
    before = len(telegram)
    await handle_update(message(1001, "/start whatever", chat_type="group"))
    assert len(telegram) == before  # в группы бот не пишет: там могут оказаться телефоны клиентов


async def test_notifications_follow_the_booking(
    telegram: list[dict], owner: httpx.AsyncClient, make_client: ClientFactory, equipment: dict
):
    renter = await make_client("ivan@test.ru", name="Иван <b>Петров</b>")
    await connect(owner, 1001)
    await connect(renter, 2002)
    telegram.clear()

    body = booking_body(equipment["id"], at(3, 9), comment="Траншея <30 м>")
    bid = (await renter.post("/api/bookings", json=body)).json()["id"]
    new = telegram[-1]
    assert new["chat_id"] == 1001 and new["parse_mode"] == "HTML"
    assert "Новая заявка" in new["text"] and "+7 (900) 111-22-33" in new["text"]
    # Пользовательский текст экранируется и не ломает разметку
    assert "Иван &lt;b&gt;Петров&lt;/b&gt;" in new["text"] and "&lt;30 м&gt;" in new["text"]
    # На localhost ссылок нет: Telegram не принимает такие адреса в кнопках
    assert "reply_markup" not in new

    await owner.post(f"/api/bookings/{bid}/confirm")
    assert telegram[-1]["chat_id"] == 2002 and "подтверждена" in telegram[-1]["text"]


async def test_blocked_bot_unlinks_chat(
    telegram: list[dict], owner: httpx.AsyncClient, renter: httpx.AsyncClient, equipment: dict
):
    await connect(owner, BLOCKED_CHAT)
    await renter.post("/api/bookings", json=booking_body(equipment["id"], at(3, 9)))
    assert (await owner.get("/api/telegram/status")).json()["connected"] is False
