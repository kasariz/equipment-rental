"""Демо-набор для показа заказчику: аккаунт владельца и аккаунт арендатора со всеми сценариями.

    python -m app.scripts.demo           # создать, если ещё нет
    python -m app.scripts.demo --reset   # удалить демо-данные и создать заново (перед каждым показом)
В Docker:
    docker compose -f docker-compose.prod.yml --env-file .env.prod exec -T backend python -m app.scripts.demo --reset

Все даты считаются от текущего момента: новые заявки «только что пришли», текущая аренда идёт сейчас.
Новые заявки сгорают через сутки, поэтому перед показом запускайте --reset.
Демо-данные живут только в аккаунтах @demo.ru из этого файла: остальные пользователи не затрагиваются.
"""

import argparse
import asyncio
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import Range

from app.core.config import settings
from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models import (
    Booking,
    BookingStatus,
    Category,
    Equipment,
    EquipmentStatus,
    Favorite,
    RateType,
    Review,
    ReviewDirection,
    User,
    UserRole,
)
from app.services.pricing import calculate

OWNER_EMAIL = "vladelec@demo.ru"
RENTER_EMAIL = "arendator@demo.ru"
DEFAULT_PASSWORD = "Demo-2026"

# Массовка: без других клиентов и владельцев не показать рейтинги, отзывы и чужие заявки
EXTRA = {
    "oleg": ("oleg.demo@demo.ru", "Олег Петренко", "+79281112233", UserRole.client),
    "natalya": ("natalya.demo@demo.ru", "Наталья Гордеева", "+79184445566", UserRole.client),
    "artem": ("artem.demo@demo.ru", "Артём Лисицын", "+79035557788", UserRole.owner),
}
DEMO_EMAILS = [OWNER_EMAIL, RENTER_EMAIL, *(e[0] for e in EXTRA.values())]


@dataclass
class Item:
    key: str
    owner: str  # "owner" — демо-владелец, иначе ключ из EXTRA
    category: str
    name: str
    address: str
    lat: float
    lon: float
    hour: int
    shift: int
    min_hours: int
    specs: dict[str, str]
    description: str
    status: EquipmentStatus = EquipmentStatus.available


ITEMS = [
    Item(
        "jcb",
        "owner",
        "excavator-loaders",
        "JCB 4CX ECO",
        "Ростов-на-Дону, улица Доватора, 150",
        47.2392,
        39.6253,
        3300,
        25000,
        4,
        {
            "Глубина копания": "5,9 м",
            "Объём ковша экскаватора": "0,24 м³",
            "Объём ковша погрузчика": "1,3 м³",
            "Высота выгрузки": "2,8 м",
            "Масса": "8,9 т",
            "Мощность двигателя": "109 л. с.",
            "Навесное оборудование": "гидромолот, вилы, планировочный ковш",
        },
        "Полноприводный экскаватор-погрузчик, 2021 год. Опытный машинист со стажем 12 лет. "
        "Траншеи, котлованы, планировка участка, погрузка грунта.",
    ),
    Item(
        "volvo",
        "owner",
        "crawler-excavators",
        "Volvo EC220E",
        "Ростов-на-Дону, проспект Шолохова, 270",
        47.2611,
        39.7986,
        4800,
        36000,
        8,
        {
            "Глубина копания": "6,7 м",
            "Объём ковша": "1,2 м³",
            "Радиус копания": "9,9 м",
            "Масса": "22,5 т",
            "Мощность двигателя": "174 л. с.",
            "Ширина гусениц": "600 мм",
            "Навесное оборудование": "гидромолот",
        },
        "Гусеничный экскаватор для котлованов и демонтажа. Доставка тралом по Ростову и области.",
    ),
    Item(
        "kubota",
        "owner",
        "mini-excavators",
        "Kubota KX057-5",
        "Ростов-на-Дону, улица Малиновского, 25",
        47.2330,
        39.6380,
        2700,
        20000,
        4,
        {
            "Глубина копания": "3,8 м",
            "Объём ковша": "0,18 м³",
            "Ширина": "1,96 м",
            "Масса": "5,6 т",
            "Мощность двигателя": "47 л. с.",
            "Тип ходовой": "резиновые гусеницы",
            "Навесное оборудование": "гидробур, ковш-планировщик",
        },
        "Компактный экскаватор для работы во дворах и на участках, не повреждает газон и плитку.",
    ),
    Item(
        "crane",
        "owner",
        "truck-cranes",
        "Галичанин КС-55713 25 т",
        "Аксай, улица Шолохова, 2",
        47.2675,
        39.8571,
        3800,
        29000,
        4,
        {
            "Грузоподъёмность": "25 т",
            "Длина стрелы": "28 м",
            "Высота подъёма": "29 м",
            "Вылет стрелы": "24 м",
            "Колёсная формула": "6×4",
            "Гусёк": "9 м",
        },
        "Автокран на шасси КАМАЗ. Монтаж плит, ферм, разгрузка оборудования. Стропальщик по запросу.",
    ),
    Item(
        "manip",
        "owner",
        "manipulators",
        "Hyundai HD120 с КМУ Kanglim",
        "Батайск, улица Луначарского, 177",
        47.1300,
        39.7505,
        3200,
        24000,
        4,
        {
            "Грузоподъёмность КМУ": "5 т",
            "Вылет стрелы": "15 м",
            "Грузоподъёмность борта": "6 т",
            "Длина борта": "6,5 м",
            "Колёсная формула": "4×2",
            "Люлька": "есть, на 2 человека",
        },
        "Перевозка и разгрузка стройматериалов, контейнеров, бытовок.",
    ),
    Item(
        "bobcat",
        "owner",
        "skid-steer-loaders",
        "Bobcat S530",
        "Ростов-на-Дону, улица Вавилова, 62",
        47.2640,
        39.6930,
        2500,
        18500,
        4,
        {
            "Грузоподъёмность": "0,8 т",
            "Объём ковша": "0,35 м³",
            "Высота выгрузки": "2,4 м",
            "Масса": "2,7 т",
            "Навесное оборудование": "щётка, вилы, бур",
        },
        "Мини-погрузчик для уборки территории, вывоза мусора и работы в стеснённых условиях.",
    ),
    Item(
        "kamaz",
        "owner",
        "dump-trucks",
        "КАМАЗ 65115 самосвал 15 т",
        "Ростов-на-Дону, Новочеркасское шоссе, 2",
        47.2405,
        39.7990,
        2300,
        17000,
        4,
        {
            "Грузоподъёмность": "15 т",
            "Объём кузова": "10 м³",
            "Колёсная формула": "6×4",
            "Тип разгрузки": "задняя",
            "Экологический класс": "Евро-5",
        },
        "Вывоз грунта и строительного мусора, доставка песка и щебня.",
        EquipmentStatus.maintenance,
    ),
    Item(
        "liebherr",
        "artem",
        "truck-cranes",
        "Liebherr LTM 1050-3.1",
        "Ростов-на-Дону, улица Текучёва, 139",
        47.2363,
        39.7151,
        7500,
        56000,
        4,
        {
            "Грузоподъёмность": "50 т",
            "Длина стрелы": "38 м",
            "Высота подъёма": "48 м",
            "Вылет стрелы": "36 м",
            "Колёсная формула": "6×6",
            "Гусёк": "16 м",
        },
        "Мобильный кран для тяжёлых монтажных работ.",
    ),
    Item(
        "cat",
        "artem",
        "excavator-loaders",
        "Caterpillar 432F2",
        "Ростов-на-Дону, улица Ленина, 101",
        47.2490,
        39.7240,
        3100,
        23500,
        4,
        {
            "Глубина копания": "5,8 м",
            "Объём ковша экскаватора": "0,2 м³",
            "Объём ковша погрузчика": "1 м³",
            "Высота выгрузки": "2,7 м",
            "Масса": "8,6 т",
            "Мощность двигателя": "100 л. с.",
            "Навесное оборудование": "гидромолот",
        },
        "Экскаватор-погрузчик с гидромолотом, работаем без выходных.",
    ),
]


async def remove_demo(session) -> int:
    result = await session.execute(delete(User).where(User.email.in_(DEMO_EMAILS)))
    await session.commit()
    return result.rowcount or 0


async def create_demo(password: str = DEFAULT_PASSWORD) -> dict[str, str]:
    tz = ZoneInfo(settings.timezone)
    now = datetime.now(tz)
    hour_now = now.replace(minute=0, second=0, microsecond=0)

    def at(days: int, hour: int) -> datetime:
        return (now + timedelta(days=days)).replace(hour=hour, minute=0, second=0, microsecond=0)

    async with SessionLocal() as session:
        if await session.scalar(select(User).where(User.email == OWNER_EMAIL)):
            return {}

        users: dict[str, User] = {
            "owner": User(
                email=OWNER_EMAIL,
                full_name="Михаил Ковалёв",
                phone="+79094561234",
                role=UserRole.owner,
                hashed_password=hash_password(password),
            ),
            "renter": User(
                email=RENTER_EMAIL,
                full_name="Анна Соколова",
                phone="+79286547890",
                role=UserRole.client,
                hashed_password=hash_password(password),
            ),
        }
        for key, (email, name, phone, role) in EXTRA.items():
            # У массовки случайные пароли: под ней никто не входит
            users[key] = User(
                email=email,
                full_name=name,
                phone=phone,
                role=role,
                hashed_password=hash_password(secrets.token_urlsafe(16)),
            )
        for u in users.values():
            u.consent_at = datetime.now(UTC)
            session.add(u)

        categories = {c.slug: c.id for c in await session.scalars(select(Category))}
        eq: dict[str, Equipment] = {}
        for it in ITEMS:
            eq[it.key] = Equipment(
                owner=users[it.owner],
                category_id=categories[it.category],
                name=it.name,
                description=it.description,
                specs=[{"name": k, "value": v} for k, v in it.specs.items()],
                address=it.address,
                latitude=it.lat,
                longitude=it.lon,
                price_per_hour=Decimal(it.hour),
                price_per_shift=Decimal(it.shift),
                min_hours=it.min_hours,
                status=it.status,
            )
            session.add(eq[it.key])
        await session.flush()

        bookings: dict[str, Booking] = {}

        def book(key, item, who, start, rate, qty, status, *, created=None, comment=None, address=None, reason=None):
            q = calculate(eq[item], rate, start, qty)
            b = Booking(
                user_id=users[who].id,
                equipment_id=eq[item].id,
                period=Range(q.start, q.end, bounds="[)"),
                rate_type=rate.value,
                quantity=qty,
                contact_phone=users[who].phone,
                comment=comment,
                delivery_address=address,
                reject_reason=reason,
                rental_price=q.total_price,
                total_price=q.total_price,
                status=status,
                created_at=created or (start - timedelta(days=2)),
            )
            session.add(b)
            bookings[key] = b

        def block(item, start_day, days, reason):
            start = at(start_day, 0)
            session.add(
                Booking(
                    user_id=eq[item].owner_id,
                    equipment_id=eq[item].id,
                    period=Range(start, start + timedelta(days=days), bounds="[)"),
                    rate_type=RateType.shift.value,
                    quantity=1,
                    contact_phone="",
                    comment=reason,
                    rental_price=0,
                    total_price=0,
                    status=BookingStatus.blocked,
                )
            )

        H, S = RateType.hourly, RateType.shift
        st = BookingStatus
        just_now = now - timedelta(minutes=35)
        # --- Техника демо-владельца: все состояния заявок ---
        book(
            "jcb_done",
            "jcb",
            "renter",
            at(-20, 8),
            S,
            2,
            st.completed,
            comment="Котлован под фундамент дома 10×12",
            address="Ростов-на-Дону, улица Орбитальная, 70",
        )
        book("jcb_oleg", "jcb", "oleg", at(-12, 9), H, 6, st.completed, comment="Траншея под канализацию")
        book(
            "jcb_active",
            "jcb",
            "natalya",
            hour_now - timedelta(hours=2),
            H,
            8,
            st.active,
            comment="Планировка участка после стройки",
            created=now - timedelta(days=1),
        )
        book(
            "jcb_new",
            "jcb",
            "renter",
            at(3, 9),
            H,
            6,
            st.pending,
            created=just_now,
            comment="Нужно выкопать траншею под водопровод, около 40 метров",
            address="Ростов-на-Дону, улица Орбитальная, 70",
        )
        book("jcb_confirmed", "jcb", "oleg", at(6, 8), S, 2, st.confirmed, created=now - timedelta(hours=20))
        block("jcb", 10, 3, "Заказ по телефону")

        book("volvo_done", "volvo", "natalya", at(-7, 8), S, 3, st.completed, comment="Демонтаж старого склада")
        book(
            "volvo_new",
            "volvo",
            "oleg",
            at(2, 8),
            S,
            1,
            st.pending,
            created=now - timedelta(hours=3),
            comment="Котлован 15×20, глубина 3 метра",
        )
        book(
            "volvo_confirmed",
            "volvo",
            "renter",
            at(8, 8),
            S,
            1,
            st.confirmed,
            created=now - timedelta(hours=26),
            address="Аксай, улица Садовая, 14",
        )
        book(
            "volvo_rejected",
            "volvo",
            "renter",
            at(1, 8),
            S,
            1,
            st.rejected,
            created=now - timedelta(days=1),
            reason="В эти даты экскаватор работает на другом объекте",
        )

        book(
            "kubota_done",
            "kubota",
            "renter",
            at(-5, 9),
            H,
            6,
            st.completed,
            comment="Ямы под столбы забора",
            address="Ростов-на-Дону, улица Орбитальная, 70",
        )
        book("kubota_cancelled", "kubota", "renter", at(4, 10), H, 4, st.cancelled, created=now - timedelta(days=2))
        book("kubota_expired", "kubota", "oleg", at(-1, 10), H, 4, st.expired, created=now - timedelta(days=3))
        block("kubota", 14, 3, "Плановое ТО")

        book("crane_old", "crane", "oleg", at(-25, 8), H, 8, st.completed, comment="Монтаж плит перекрытия")
        book("crane_done", "crane", "renter", at(-3, 8), S, 1, st.completed, comment="Разгрузка металлоконструкций")
        book(
            "manip_new",
            "manip",
            "natalya",
            at(5, 10),
            H,
            5,
            st.pending,
            created=now - timedelta(hours=1),
            comment="Перевезти бытовку 6 метров, разгрузить на участке",
        )
        block("kamaz", 0, 5, "Ремонт ходовой")

        # --- Другой владелец: у арендатора рейтинг от двух владельцев ---
        book("cat_done", "cat", "renter", at(-15, 8), S, 1, st.completed)
        await session.flush()

        def review(booking_key, direction, rating, text, days_ago):
            b = bookings[booking_key]
            about_owner = direction == ReviewDirection.about_owner
            owner_id = next(e.owner_id for e in eq.values() if e.id == b.equipment_id)
            author = b.user_id if about_owner else owner_id
            subject = owner_id if about_owner else b.user_id
            session.add(
                Review(
                    booking_id=b.id,
                    direction=direction,
                    author_id=author,
                    subject_id=subject,
                    rating=rating,
                    text=text,
                    created_at=now - timedelta(days=days_ago),
                )
            )

        about_owner, about_renter = ReviewDirection.about_owner, ReviewDirection.about_renter
        review(
            "jcb_done",
            about_owner,
            5,
            "Приехали минута в минуту, машинист сам предложил, как лучше развернуть котлован.",
            17,
        )
        review("jcb_oleg", about_owner, 4, "Работой доволен, но пришлось подождать полчаса утром.", 11)
        review(
            "volvo_done",
            about_owner,
            5,
            "Мощная машина и аккуратный экскаваторщик. Демонтаж закончили на день раньше.",
            3,
        )
        review("crane_old", about_owner, 5, "Кран в отличном состоянии, всё по договорённости.", 24)
        review(
            "crane_done", about_owner, 4, "Хороший кран, но заезд на участок пришлось согласовывать дольше обычного.", 2
        )
        review("cat_done", about_owner, 5, "Артём на связи в любое время, рекомендую.", 13)
        review("jcb_done", about_renter, 5, "Объект подготовлен, подъезд свободен, расчёт сразу после работы.", 17)
        review("cat_done", about_renter, 5, "Чёткий клиент, всё как договорились.", 13)
        review("jcb_oleg", about_renter, 4, "Нормальный клиент, но задержал технику на час сверх оговорённого.", 11)
        review("volvo_done", about_renter, 5, "Всё организовано отлично.", 3)
        review("kubota_cancelled", about_renter, 3, "Отменил заказ за день до начала, технику уже держали под него.", 1)

        for item in ("volvo", "crane", "liebherr"):
            session.add(Favorite(user_id=users["renter"].id, equipment_id=eq[item].id))
        await session.commit()
    return {"owner": OWNER_EMAIL, "renter": RENTER_EMAIL, "password": password}


async def main(reset: bool, password: str) -> None:
    async with SessionLocal() as session:
        if reset:
            print(f"Удалено демо-аккаунтов: {await remove_demo(session)}")
    created = await create_demo(password)
    if not created:
        print("Демо-данные уже есть. Чтобы пересоздать их со свежими датами: --reset")
        return
    print("Демо-данные готовы. Вход:")
    print(f"  Владелец:   {created['owner']} / {created['password']}")
    print(f"  Арендатор:  {created['renter']} / {created['password']}")
    print("Новые заявки сгорают через сутки: перед показом запускайте с --reset")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--reset", action="store_true", help="удалить демо-данные и создать заново")
    parser.add_argument("--password", default=DEFAULT_PASSWORD, help="пароль обоих демо-аккаунтов")
    args = parser.parse_args()
    asyncio.run(main(args.reset, args.password))
