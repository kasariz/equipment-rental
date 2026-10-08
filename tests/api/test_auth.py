import httpx

from tests.conftest import PASSWORD, ClientFactory


async def test_register_logs_in_and_me_works(make_client: ClientFactory):
    c = await make_client("Ivan@Mail.RU", name="  Иван  ")
    me = (await c.get("/api/auth/me")).json()
    assert me["email"] == "ivan@mail.ru"  # email приводится к нижнему регистру
    assert me["full_name"] == "Иван"
    assert me["role"] == "client"
    assert me["telegram_connected"] is False


async def test_auth_cookie_is_http_only(anon: httpx.AsyncClient):
    r = await anon.post(
        "/api/auth/register", json={"consent": True, "email": "a@test.ru", "password": PASSWORD, "full_name": "Аня"}
    )
    cookie = r.headers["set-cookie"].lower()
    assert "httponly" in cookie and "samesite=lax" in cookie


async def test_duplicate_email_is_rejected_case_insensitively(make_client: ClientFactory, anon: httpx.AsyncClient):
    await make_client("dup@test.ru")
    r = await anon.post(
        "/api/auth/register",
        json={"consent": True, "email": "DUP@test.ru", "password": PASSWORD, "full_name": "Двойник"},
    )
    assert r.status_code == 409


async def test_cannot_register_as_admin(anon: httpx.AsyncClient):
    r = await anon.post(
        "/api/auth/register",
        json={"consent": True, "email": "x@test.ru", "password": PASSWORD, "full_name": "Хакер", "role": "admin"},
    )
    assert r.status_code == 422


async def test_wrong_password_and_unknown_email_look_the_same(make_client: ClientFactory, anon: httpx.AsyncClient):
    await make_client("user@test.ru")
    wrong = await anon.post("/api/auth/login", json={"email": "user@test.ru", "password": "nope-nope"})
    unknown = await anon.post("/api/auth/login", json={"email": "ghost@test.ru", "password": "nope-nope"})
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json()  # по ответу нельзя узнать, есть ли такой email


async def test_logout(renter: httpx.AsyncClient):
    assert (await renter.post("/api/auth/logout")).status_code == 204
    assert (await renter.get("/api/auth/me")).status_code == 401


async def test_broken_token_is_401(anon: httpx.AsyncClient):
    anon.cookies.set("access_token", "garbage")
    assert (await anon.get("/api/auth/me")).status_code == 401
