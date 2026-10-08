import httpx
import pytest
from sqlalchemy import update

from app.db.session import SessionLocal
from app.models import User, UserRole
from tests.conftest import ClientFactory, at, booking_body


async def completed_booking(
    owner: httpx.AsyncClient, renter: httpx.AsyncClient, equipment_id: int, day: int = 3
) -> int:
    bid = (await renter.post("/api/bookings", json=booking_body(equipment_id, at(day, 9)))).json()["id"]
    for action in ("confirm", "start", "complete"):
        assert (await owner.post(f"/api/bookings/{bid}/{action}")).status_code == 200
    return bid


async def test_review_after_completed_rental(owner: httpx.AsyncClient, renter: httpx.AsyncClient, equipment: dict):
    bid = (await renter.post("/api/bookings", json=booking_body(equipment["id"], at(3, 9)))).json()["id"]
    early = await renter.post(f"/api/bookings/{bid}/review", json={"rating": 5})
    assert early.status_code == 409  # пока заявка в работе, отзыв не оставить

    for action in ("confirm", "start", "complete"):
        await owner.post(f"/api/bookings/{bid}/{action}")
    r = await renter.post(f"/api/bookings/{bid}/review", json={"rating": 4, "text": "  Приехали вовремя  "})
    assert r.status_code == 201
    assert r.json()["author_name"] == "Анна К."  # полное имя автора не раскрывается
    assert r.json()["text"] == "Приехали вовремя"

    again = await renter.post(f"/api/bookings/{bid}/review", json={"rating": 1})
    assert again.status_code == 409
    assert (await renter.get("/api/my/bookings")).json()[0]["reviewed"] is True


async def test_renter_can_review_owner_who_rejected(
    owner: httpx.AsyncClient, renter: httpx.AsyncClient, equipment: dict
):
    bid = (await renter.post("/api/bookings", json=booking_body(equipment["id"], at(3, 9)))).json()["id"]
    await owner.post(f"/api/bookings/{bid}/reject", json={"reason": "Передумал"})
    assert (await renter.post(f"/api/bookings/{bid}/review", json={"rating": 1})).status_code == 201


async def test_renter_cannot_review_after_own_cancel(
    owner: httpx.AsyncClient, renter: httpx.AsyncClient, equipment: dict
):
    bid = (await renter.post("/api/bookings", json=booking_body(equipment["id"], at(3, 9)))).json()["id"]
    await renter.post(f"/api/bookings/{bid}/cancel")
    assert (await renter.post(f"/api/bookings/{bid}/review", json={"rating": 1})).status_code == 409
    # А вот владелец может оценить арендатора, который отменил бронь
    assert (await owner.post(f"/api/bookings/{bid}/renter-review", json={"rating": 2})).status_code == 201


async def test_owner_reviews_renter_and_sees_rating_in_requests(
    owner: httpx.AsyncClient, renter: httpx.AsyncClient, make_client: ClientFactory, equipment: dict
):
    bid = await completed_booking(owner, renter, equipment["id"])
    r = await owner.post(f"/api/bookings/{bid}/renter-review", json={"rating": 5, "text": "Вовремя оплатил"})
    assert r.status_code == 201 and r.json()["direction"] == "about_renter"
    assert (await owner.post(f"/api/bookings/{bid}/renter-review", json={"rating": 5})).status_code == 409
    # Оба отзыва по одной брони не мешают друг другу
    assert (await renter.post(f"/api/bookings/{bid}/review", json={"rating": 4})).status_code == 201

    # Другой владелец видит рейтинг этого арендатора в новой заявке
    other_owner = await make_client("owner2@test.ru", role="owner")
    from tests.conftest import create_equipment

    eq2 = await create_equipment(other_owner, name="Кран")
    await renter.post("/api/bookings", json=booking_body(eq2["id"], at(5, 9)))
    client = (await other_owner.get("/api/owner/bookings")).json()[0]["client"]
    assert (client["rating"], client["reviews_count"]) == (5.0, 1)
    reviews = (await other_owner.get(f"/api/renters/{client['id']}/reviews")).json()
    assert reviews["items"][0]["text"] == "Вовремя оплатил"

    # Рейтинг владельца не смешивается с рейтингом арендатора
    assert (await renter.get("/api/my/ratings")).json() == {
        "as_owner": {"rating": None, "count": 0},
        "as_renter": {"rating": 5.0, "count": 1},
    }


async def test_renter_reviews_are_only_for_owners(renter: httpx.AsyncClient):
    me = (await renter.get("/api/auth/me")).json()
    assert (await renter.get(f"/api/renters/{me['id']}/reviews")).status_code == 403


async def test_stranger_owner_cannot_review_renter(
    owner: httpx.AsyncClient, renter: httpx.AsyncClient, make_client: ClientFactory, equipment: dict
):
    bid = await completed_booking(owner, renter, equipment["id"])
    stranger = await make_client("s2@test.ru", role="owner")
    assert (await stranger.post(f"/api/bookings/{bid}/renter-review", json={"rating": 1})).status_code == 404


async def test_only_the_renter_can_review(
    owner: httpx.AsyncClient, renter: httpx.AsyncClient, make_client: ClientFactory, equipment: dict
):
    bid = await completed_booking(owner, renter, equipment["id"])
    stranger = await make_client("s@test.ru")
    assert (await stranger.post(f"/api/bookings/{bid}/review", json={"rating": 1})).status_code == 404


@pytest.mark.parametrize("rating", [0, 6])
async def test_rating_range(owner: httpx.AsyncClient, renter: httpx.AsyncClient, equipment: dict, rating: int):
    bid = await completed_booking(owner, renter, equipment["id"])
    assert (await renter.post(f"/api/bookings/{bid}/review", json={"rating": rating})).status_code == 422


async def test_owner_rating_in_catalog_and_details(
    owner: httpx.AsyncClient, renter: httpx.AsyncClient, anon: httpx.AsyncClient, equipment: dict
):
    for day, rating in [(3, 5), (5, 4)]:
        bid = await completed_booking(owner, renter, equipment["id"], day)
        await renter.post(f"/api/bookings/{bid}/review", json={"rating": rating})

    item = (await anon.get("/api/equipment")).json()["items"][0]
    assert (item["owner_rating"], item["owner_reviews_count"]) == (4.5, 2)
    details = (await anon.get(f"/api/equipment/{equipment['id']}")).json()
    assert details["owner"]["rating"] == 4.5
    reviews = (await anon.get(f"/api/owners/{details['owner']['id']}/reviews")).json()
    assert reviews["count"] == 2 and reviews["items"][0]["equipment_name"] == "JCB 3CX"


@pytest.fixture
async def admin(make_client: ClientFactory) -> httpx.AsyncClient:
    client = await make_client("admin@test.ru", name="Админ Админов")
    async with SessionLocal() as session:
        await session.execute(update(User).where(User.email == "admin@test.ru").values(role=UserRole.admin))
        await session.commit()
    return client


async def test_admin_api_is_closed_to_others(owner: httpx.AsyncClient, renter: httpx.AsyncClient):
    for c in (owner, renter):
        assert (await c.get("/api/admin/users")).status_code == 403
        assert (await c.delete("/api/admin/bookings/1")).status_code == 403


async def test_admin_deletes_booking_without_archive(
    admin: httpx.AsyncClient, owner: httpx.AsyncClient, renter: httpx.AsyncClient, equipment: dict
):
    bid = (await renter.post("/api/bookings", json=booking_body(equipment["id"], at(3, 9)))).json()["id"]
    assert (await admin.get("/api/admin/bookings")).json()["items"][0]["id"] == bid  # админ видит все заявки
    assert (await admin.delete(f"/api/admin/bookings/{bid}")).status_code == 204
    assert (await renter.get("/api/my/bookings")).json() == []
    assert (await owner.get("/api/owner/bookings")).json() == []  # ни в текущих, ни в архиве


async def test_admin_deletes_users_and_equipment(
    admin: httpx.AsyncClient,
    owner: httpx.AsyncClient,
    renter: httpx.AsyncClient,
    anon: httpx.AsyncClient,
    equipment: dict,
):
    users = {u["email"]: u for u in (await admin.get("/api/admin/users")).json()["items"]}
    assert users["owner@test.ru"]["equipment_count"] == 1
    assert (await admin.delete(f"/api/admin/users/{users['admin@test.ru']['id']}")).status_code == 409  # себя нельзя

    await renter.post("/api/bookings", json=booking_body(equipment["id"], at(3, 9)))
    assert (await admin.delete(f"/api/admin/equipment/{equipment['id']}")).status_code == 204  # даже с бронью
    assert (await anon.get("/api/equipment")).json()["total"] == 0

    assert (await admin.delete(f"/api/admin/users/{users['client@test.ru']['id']}")).status_code == 204
    assert (await renter.get("/api/auth/me")).status_code == 401


async def test_admin_manages_categories(admin: httpx.AsyncClient, owner: httpx.AsyncClient, anon: httpx.AsyncClient):
    r = await admin.post(
        "/api/admin/categories",
        json={
            "name": "Бетоносмесители",
            "spec_template": [
                {"name": "Объём барабана", "example": "9 м³"},
                {"name": "Объём барабана", "example": "дубль"},  # повтор названия отбрасывается
            ],
        },
    )
    assert r.status_code == 201
    category = r.json()
    assert category["slug"] == "betonosmesiteli"
    assert category["spec_template"] == [{"name": "Объём барабана", "example": "9 м³"}]
    assert (await admin.post("/api/admin/categories", json={"name": "Бетоносмесители"})).status_code == 409

    # Новая категория сразу доступна владельцам и в фильтре каталога
    from tests.conftest import create_equipment

    await create_equipment(owner, category_id=category["id"], name="Миксер КАМАЗ")
    found = (await anon.get("/api/equipment", params={"category": "betonosmesiteli"})).json()
    assert [i["name"] for i in found["items"]] == ["Миксер КАМАЗ"]

    assert (await admin.delete(f"/api/admin/categories/{category['id']}")).status_code == 409  # в ней есть техника
    renamed = await admin.put(f"/api/admin/categories/{category['id']}", json={"name": "Автобетоносмесители"})
    assert renamed.json()["slug"] == "betonosmesiteli"  # ссылки на каталог не ломаются


async def test_admin_search_filters_and_paging(
    admin: httpx.AsyncClient, make_client: ClientFactory, owner: httpx.AsyncClient, equipment: dict
):
    for i in range(7):
        await make_client(f"user{i}@test.ru", name=f"Пользователь Номер{i}")
    phone_user = await make_client("phone@test.ru", name="Телефон Тестов")
    await phone_user.post(
        "/api/bookings", json=booking_body(equipment["id"], at(3, 9), contact_phone="8 961 555-44-33")
    )

    page = (await admin.get("/api/admin/users", params={"limit": 3})).json()
    # 7 пользователей + «телефон» + админ + владелец из фикстур
    assert len(page["items"]) == 3 and page["total"] == 10
    second = (await admin.get("/api/admin/users", params={"limit": 3, "offset": 3})).json()
    assert {u["id"] for u in page["items"]}.isdisjoint({u["id"] for u in second["items"]})

    async def emails(**params) -> set[str]:
        return {u["email"] for u in (await admin.get("/api/admin/users", params=params)).json()["items"]}

    assert await emails(q="номер3") == {"user3@test.ru"}
    assert await emails(q="8 961 555") == {"phone@test.ru"}  # телефон ищется по цифрам
    assert await emails(role="owner") == {"owner@test.ru"}
    assert await emails(q="100%") == set()

    # Фильтр по аккаунту: брони клиента и брони на технику владельца
    pid = next(u["id"] for u in (await admin.get("/api/admin/users", params={"q": "phone@"})).json()["items"])
    by_client = (await admin.get("/api/admin/bookings", params={"user_id": pid})).json()
    owner_id = (await owner.get("/api/auth/me")).json()["id"]
    by_owner = (await admin.get("/api/admin/bookings", params={"user_id": owner_id})).json()
    assert by_client["total"] == by_owner["total"] == 1
    assert (await admin.get("/api/admin/bookings", params={"status": "cancelled"})).json()["total"] == 0
    assert (await admin.get("/api/admin/equipment", params={"user_id": owner_id})).json()["total"] == 1
    assert (await admin.get("/api/admin/equipment", params={"q": "нет такой"})).json()["total"] == 0
