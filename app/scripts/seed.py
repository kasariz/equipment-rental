"""Демо-данные: владелец с техникой вокруг Ростова-на-Дону и клиент с заявками.

Запуск: python -m app.scripts.seed
Повторный запуск ничего не дублирует.
"""

import asyncio
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import Range

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models import Booking, BookingStatus, Category, Equipment, RateType, User, UserRole
from app.services.pricing import calculate

DEMO_EMAIL = "owner@demo.ru"
DEMO_PASSWORD = "demo12345"
CLIENT_EMAIL = "client@demo.ru"
MSK = timezone(timedelta(hours=3))

# (категория, название, адрес, широта, долгота, ₽/час, ₽/смена, мин. часов, оператор ₽/час, характеристики)
ITEMS = [
    (
        "excavator-loaders",
        "JCB 3CX Super",
        "Ростов-на-Дону, Западный жилмассив",
        47.2216,
        39.6254,
        2500,
        18000,
        4,
        600,
        {"Глубина копания": "5,9 м", "Объём ковша": "1 м³", "Масса": "8,3 т"},
    ),
    (
        "excavator-loaders",
        "Hidromek HMK 102B",
        "Ростов-на-Дону, Северный",
        47.2895,
        39.7178,
        2300,
        17000,
        4,
        600,
        {"Глубина копания": "5,7 м", "Объём ковша": "1,1 м³", "Масса": "8,5 т"},
    ),
    (
        "excavator-loaders",
        "Terex 860 Elite",
        "Батайск, ул. Северная",
        47.1462,
        39.7449,
        2200,
        16000,
        4,
        None,
        {"Глубина копания": "5,8 м", "Объём ковша": "1 м³"},
    ),
    (
        "mini-excavators",
        "Kubota U27-4",
        "Ростов-на-Дону, Левенцовка",
        47.2116,
        39.5958,
        2000,
        14500,
        4,
        500,
        {"Глубина копания": "2,8 м", "Ширина": "1,5 м", "Масса": "2,7 т"},
    ),
    (
        "mini-excavators",
        "Takeuchi TB216",
        "Аксай, пр. Ленина",
        47.2681,
        39.8689,
        1900,
        14000,
        4,
        500,
        {"Глубина копания": "2,5 м", "Ширина": "1 м", "Масса": "1,7 т"},
    ),
    (
        "crawler-excavators",
        "Komatsu PC200-8",
        "Ростов-на-Дону, Военвед",
        47.2487,
        39.6409,
        3800,
        28000,
        8,
        700,
        {"Глубина копания": "6,6 м", "Объём ковша": "0,9 м³", "Масса": "20 т"},
    ),
    (
        "crawler-excavators",
        "Hyundai R220LC-9S",
        "Ростов-на-Дону, промзона Заречная",
        47.1903,
        39.7230,
        4000,
        30000,
        8,
        700,
        {"Глубина копания": "6,7 м", "Объём ковша": "1,1 м³", "Масса": "22 т"},
    ),
    (
        "wheel-loaders",
        "SDLG LG936L",
        "Ростов-на-Дону, Каменка",
        47.2709,
        39.6801,
        2400,
        18000,
        4,
        600,
        {"Объём ковша": "1,8 м³", "Грузоподъёмность": "3 т"},
    ),
    (
        "wheel-loaders",
        "Lonking CDM833",
        "Батайск, Авиагородок",
        47.1243,
        39.7671,
        2300,
        17000,
        4,
        None,
        {"Объём ковша": "1,8 м³", "Грузоподъёмность": "3 т"},
    ),
    (
        "truck-cranes",
        "Ивановец КС-45717 25 т",
        "Ростов-на-Дону, Нариманова",
        47.2163,
        39.6897,
        3200,
        24000,
        4,
        700,
        {"Грузоподъёмность": "25 т", "Длина стрелы": "21,7 м"},
    ),
    (
        "truck-cranes",
        "Галичанин КС-55729 32 т",
        "Ростов-на-Дону, Александровка",
        47.2307,
        39.7907,
        3900,
        29000,
        4,
        700,
        {"Грузоподъёмность": "32 т", "Длина стрелы": "30,2 м"},
    ),
    (
        "manipulators",
        "КАМАЗ 65115 с КМУ Kanglim",
        "Ростов-на-Дону, Сельмаш",
        47.2622,
        39.7457,
        2600,
        19000,
        4,
        600,
        {"Грузоподъёмность КМУ": "7 т", "Борт": "6,2 м"},
    ),
    (
        "dump-trucks",
        "КАМАЗ 6520 25 т",
        "Ростов-на-Дону, Мясникован",
        47.2462,
        39.7795,
        2000,
        15000,
        4,
        500,
        {"Грузоподъёмность": "20 т", "Объём кузова": "16 м³"},
    ),
    (
        "dump-trucks",
        "Shacman SX3258 25 т",
        "Аксай, промзона",
        47.2528,
        39.8960,
        2100,
        15500,
        4,
        500,
        {"Грузоподъёмность": "25 т", "Объём кузова": "20 м³"},
    ),
    (
        "rollers",
        "Bomag BW 213 D-5",
        "Ростов-на-Дону, Темерник",
        47.2533,
        39.6982,
        2600,
        19000,
        4,
        600,
        {"Масса": "12,6 т", "Ширина вальца": "2,1 м"},
    ),
    (
        "rollers",
        "Дорожный каток ДУ-47Б",
        "Ростов-на-Дону, Пролетарский район",
        47.2259,
        39.7612,
        1800,
        13000,
        4,
        500,
        {"Масса": "6 т", "Ширина вальца": "1,7 м"},
    ),
]


async def seed_equipment() -> None:
    async with SessionLocal() as session:
        owner = await session.scalar(select(User).where(User.email == DEMO_EMAIL))
        if owner is not None:
            print("Демо-техника уже есть, пропускаю")
            return

        owner = User(
            email=DEMO_EMAIL,
            hashed_password=hash_password(DEMO_PASSWORD),
            full_name="Сергей Демидов",
            phone="+79000000000",
            role=UserRole.owner,
        )
        session.add(owner)
        categories = {c.slug: c.id for c in await session.scalars(select(Category))}

        for slug, name, address, lat, lon, hour, shift, min_h, op, specs in ITEMS:
            session.add(
                Equipment(
                    owner=owner,
                    category_id=categories[slug],
                    name=name,
                    address=address,
                    latitude=lat,
                    longitude=lon,
                    # Цены с оператором: к ставке за технику прибавляем работу машиниста
                    price_per_hour=Decimal(hour + (op or 500)),
                    price_per_shift=Decimal(shift + 8 * (op or 500)),
                    min_hours=min_h,
                    specs=[{"name": k, "value": v} for k, v in specs.items()],
                    description="Техника в рабочем состоянии, регулярное ТО. Доставка тралом по договорённости.",
                )
            )
        await session.commit()
        print(f"Готово: {len(ITEMS)} единиц техники. Вход владельца: {DEMO_EMAIL} / {DEMO_PASSWORD}")


async def seed_bookings() -> None:
    """Клиент и две заявки на технику демо-владельца, чтобы раздел «Заявки» не был пустым."""
    async with SessionLocal() as session:
        if await session.scalar(select(User).where(User.email == CLIENT_EMAIL)):
            print("Демо-клиент уже есть, пропускаю")
            return
        client = User(
            email=CLIENT_EMAIL,
            hashed_password=hash_password(DEMO_PASSWORD),
            full_name="Ирина Строева",
            phone="+79051234567",
        )
        session.add(client)
        owner = await session.scalar(select(User).where(User.email == DEMO_EMAIL))
        items = list(await session.scalars(select(Equipment).where(Equipment.owner_id == owner.id).limit(2)))

        day = datetime.now(MSK).replace(hour=8, minute=0, second=0, microsecond=0)
        plans = [  # (техника, через сколько дней, тариф, количество, статус, комментарий)
            (items[0], 2, RateType.hourly, 6, BookingStatus.pending, "Траншея под водопровод, около 40 метров"),
            (items[1], 4, RateType.shift, 2, BookingStatus.confirmed, None),
        ]
        for eq, days, rate, qty, status, comment in plans:
            q = calculate(eq, rate, day + timedelta(days=days), qty)
            session.add(
                Booking(
                    user=client,
                    equipment_id=eq.id,
                    period=Range(q.start, q.end, bounds="[)"),
                    rate_type=rate.value,
                    quantity=qty,
                    contact_phone=client.phone,
                    delivery_address="Ростов-на-Дону, ул. Малиновского, участок 12",
                    comment=comment,
                    rental_price=q.total_price,
                    total_price=q.total_price,
                    status=status,
                )
            )
        await session.commit()
        print(f"Готово: демо-клиент {CLIENT_EMAIL} / {DEMO_PASSWORD} и 2 заявки")


async def main() -> None:
    await seed_equipment()
    await seed_bookings()


if __name__ == "__main__":
    asyncio.run(main())
