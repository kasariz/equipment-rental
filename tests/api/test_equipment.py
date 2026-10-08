import io

import httpx
from PIL import Image

from tests.conftest import ClientFactory, at, booking_body, create_equipment


async def test_only_owners_can_add_equipment(equipment: dict, renter: httpx.AsyncClient, anon: httpx.AsyncClient):
    assert equipment["owner"]["full_name"] == "Пётр Владелец"
    body = {"name": "X", "category_id": 1, "address": "Где-то", "latitude": 47, "longitude": 39, "price_per_hour": 1}
    assert (await renter.post("/api/equipment", json=body)).status_code == 403
    assert (await anon.post("/api/equipment", json=body)).status_code == 401


async def test_categories_have_spec_templates(anon: httpx.AsyncClient):
    categories = {c["slug"]: c for c in (await anon.get("/api/categories")).json()}
    assert len(categories) >= 16
    template = {i["name"]: i["example"] for i in categories["excavator-loaders"]["spec_template"]}
    assert template["Глубина копания"] == "5,9 м"
    assert all(5 <= len(c["spec_template"]) <= 10 for c in categories.values())
    # У каждой характеристики есть пример значения в своих единицах
    assert all(i["example"] for c in categories.values() for i in c["spec_template"])
    dump = {i["name"]: i["example"] for i in categories["dump-trucks"]["spec_template"]}
    assert dump["Грузоподъёмность"] == "20 т" and dump["Колёсная формула"] == "6×4"


async def test_address_is_required(owner: httpx.AsyncClient):
    categories = (await owner.get("/api/categories")).json()
    body = {"name": "Кран", "category_id": categories[0]["id"], "latitude": 47, "longitude": 39, "price_per_hour": 3000}
    assert (await owner.post("/api/equipment", json=body)).status_code == 422


async def test_specs_keep_their_order(owner: httpx.AsyncClient):
    specs = [{"name": n, "value": "1"} for n in ["Масса", "Глубина копания", "Ширина"]]
    eq = await create_equipment(owner, specs=specs)
    assert [s["name"] for s in eq["specs"]] == ["Масса", "Глубина копания", "Ширина"]


async def test_catalog_filters(owner: httpx.AsyncClient, anon: httpx.AsyncClient):
    categories = {c["slug"]: c["id"] for c in (await anon.get("/api/categories")).json()}
    await create_equipment(owner, name="JCB рядом", price_per_hour=2500, latitude=47.2357, longitude=39.7015)
    await create_equipment(
        owner,
        name="Кран в Батайске",
        category_id=categories["truck-cranes"],
        price_per_hour=3500,
        latitude=47.1462,
        longitude=39.7449,
    )

    async def names(**params) -> list[str]:
        r = await anon.get("/api/equipment", params=params)
        assert r.status_code == 200, r.text
        return [i["name"] for i in r.json()["items"]]

    assert await names(category="truck-cranes") == ["Кран в Батайске"]
    assert await names(price_max=3000) == ["JCB рядом"]
    assert await names(q="кран") == ["Кран в Батайске"]  # без учёта регистра
    assert await names(q="100%") == []  # спецсимволы LIKE экранируются
    near = (await anon.get("/api/equipment", params={"lat": 47.2357, "lon": 39.7015, "sort": "distance"})).json()
    assert [i["name"] for i in near["items"]] == ["JCB рядом", "Кран в Батайске"]
    assert near["items"][0]["distance_km"] == 0
    assert await names(lat=47.2357, lon=39.7015, radius_km=5) == ["JCB рядом"]
    assert (await anon.get("/api/equipment", params={"sort": "distance"})).status_code == 422


async def test_hidden_equipment(owner: httpx.AsyncClient, anon: httpx.AsyncClient, equipment: dict):
    eid = equipment["id"]
    r = await owner.patch(f"/api/equipment/{eid}", json={"status": "maintenance"})
    assert r.json()["status"] == "maintenance"
    assert (await anon.get("/api/equipment")).json()["total"] == 0
    assert (await anon.get(f"/api/equipment/{eid}")).status_code == 404
    assert (await owner.get(f"/api/equipment/{eid}")).status_code == 200


async def test_other_owner_cannot_edit(make_client: ClientFactory, equipment: dict):
    stranger = await make_client("other@test.ru", role="owner")
    r = await stranger.patch(f"/api/equipment/{equipment['id']}", json={"name": "Моё"})
    assert r.status_code == 403


async def test_patch_cannot_null_required_fields(owner: httpx.AsyncClient, equipment: dict):
    r = await owner.patch(f"/api/equipment/{equipment['id']}", json={"price_per_hour": None})
    assert r.status_code == 422


def image_bytes(fmt: str = "PNG", size: tuple[int, int] = (2400, 1800)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, (240, 180, 10)).save(buf, fmt)
    return buf.getvalue()


async def test_photo_upload_resizes_and_serves_webp(owner: httpx.AsyncClient, equipment: dict):
    eid = equipment["id"]
    r = await owner.post(f"/api/equipment/{eid}/photos", files=[("files", ("a.png", image_bytes(), "image/png"))])
    assert r.status_code == 201, r.text
    url = r.json()[0]["url"]
    served = await owner.get(url)
    assert served.status_code == 200
    img = Image.open(io.BytesIO(served.content))
    assert img.format == "WEBP" and max(img.size) == 1600

    # Карточка в каталоге получает обложку
    assert (await owner.get(f"/api/equipment/{eid}")).json()["cover_url"] == url


async def test_fake_image_is_rejected(owner: httpx.AsyncClient, equipment: dict):
    files = [("files", ("virus.jpg", b"definitely not an image", "image/jpeg"))]
    r = await owner.post(f"/api/equipment/{equipment['id']}/photos", files=files)
    assert r.status_code == 422


async def test_cannot_delete_equipment_with_active_booking(
    owner: httpx.AsyncClient, renter: httpx.AsyncClient, equipment: dict
):
    r = await renter.post("/api/bookings", json=booking_body(equipment["id"], at(3, 9)))
    assert r.status_code == 201
    assert (await owner.delete(f"/api/equipment/{equipment['id']}")).status_code == 409
