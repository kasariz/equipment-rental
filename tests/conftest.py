"""Общая подготовка тестов.

Тесты работают с отдельной базой (по умолчанию rental_test) в том же PostgreSQL, что и разработка.
Перед запуском база пересоздаётся и прогоняются все миграции — заодно проверяются и они.
"""

import os
import tempfile

# Окружение задаём до импорта приложения: настройки читаются при импорте
os.environ["POSTGRES_DB"] = os.environ.get("TEST_POSTGRES_DB", "rental_test")
os.environ["TELEGRAM_BOT_TOKEN"] = ""
os.environ["MEDIA_DIR"] = tempfile.mkdtemp(prefix="rental-test-media-")

import asyncio
from collections.abc import AsyncIterator, Awaitable, Callable
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import asyncpg
import httpx
import pytest
from alembic.config import Config
from sqlalchemy import text

from alembic import command
from app.core.config import settings
from app.db.session import SessionLocal, engine
from app.main import app

MSK = ZoneInfo("Europe/Moscow")
PASSWORD = "secret123"


async def _recreate_database() -> None:
    conn = await asyncpg.connect(
        user=settings.postgres_user,
        password=settings.postgres_password,
        host=settings.postgres_host,
        port=settings.postgres_port,
        database="postgres",
    )
    try:
        await conn.execute(f'DROP DATABASE IF EXISTS "{settings.postgres_db}" WITH (FORCE)')
        await conn.execute(f'CREATE DATABASE "{settings.postgres_db}"')
    finally:
        await conn.close()


@pytest.fixture(scope="session")
def database() -> None:
    assert settings.postgres_db.endswith("_test"), "Тесты должны работать с отдельной базой *_test"
    asyncio.run(_recreate_database())
    command.upgrade(Config("alembic.ini"), "head")


@pytest.fixture
async def db(database: None) -> AsyncIterator[None]:
    """Чистые таблицы перед каждым тестом. Справочник категорий из миграции остаётся"""
    async with SessionLocal() as session:
        await session.execute(text("TRUNCATE users, equipment, equipment_photos, bookings RESTART IDENTITY CASCADE"))
        await session.commit()
    yield
    # У каждого теста свой цикл событий, а соединения пула привязаны к циклу — закрываем их
    await engine.dispose()


ClientFactory = Callable[..., Awaitable[httpx.AsyncClient]]


@pytest.fixture
async def make_client(db: None) -> AsyncIterator[ClientFactory]:
    """Создаёт HTTP-клиента со своими cookie. С email — сразу регистрирует и входит"""
    clients: list[httpx.AsyncClient] = []

    async def factory(email: str | None = None, *, role: str = "client", name: str = "Тест Тестов"):
        c = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")
        clients.append(c)
        if email:
            r = await c.post(
                "/api/auth/register",
                json={"email": email, "password": PASSWORD, "full_name": name, "role": role},
            )
            assert r.status_code == 201, r.text
        return c

    yield factory
    for c in clients:
        await c.aclose()


@pytest.fixture
async def anon(make_client: ClientFactory) -> httpx.AsyncClient:
    return await make_client()


@pytest.fixture
async def owner(make_client: ClientFactory) -> httpx.AsyncClient:
    return await make_client("owner@test.ru", role="owner", name="Пётр Владелец")


@pytest.fixture
async def renter(make_client: ClientFactory) -> httpx.AsyncClient:
    return await make_client("client@test.ru", name="Анна Клиентова")


async def create_equipment(owner: httpx.AsyncClient, **overrides) -> dict:
    categories = (await owner.get("/api/categories")).json()
    body = {
        "name": "JCB 3CX",
        "category_id": categories[0]["id"],
        "latitude": 47.2357,
        "longitude": 39.7015,
        "price_per_hour": 2500,
        "price_per_shift": 18000,
        "min_hours": 4,
        "operator_available": True,
        "operator_price_per_hour": 600,
        "specs": [{"name": "Масса", "value": "8 т"}],
    } | overrides
    r = await owner.post("/api/equipment", json=body)
    assert r.status_code == 201, r.text
    return r.json()


@pytest.fixture
async def equipment(owner: httpx.AsyncClient) -> dict:
    return await create_equipment(owner)


def at(days: int, hour: int) -> str:
    """Начало аренды через days дней в hour:00 по Москве, в ISO-формате с часовым поясом"""
    d = (datetime.now(MSK) + timedelta(days=days)).replace(hour=hour, minute=0, second=0, microsecond=0)
    return d.isoformat()


def booking_body(equipment_id: int, start: str, **overrides) -> dict:
    return {
        "equipment_id": equipment_id,
        "rate_type": "hourly",
        "start": start,
        "quantity": 4,
        "with_operator": False,
        "contact_phone": "+7 900 111-22-33",
    } | overrides
