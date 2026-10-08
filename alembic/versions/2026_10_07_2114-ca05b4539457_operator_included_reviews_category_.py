"""Оператор всегда включён в цену, отзывы, шаблоны характеристик, новые категории, нормализация телефонов

Revision ID: ca05b4539457
Revises: ac001aedae3f
Create Date: 2026-10-07 21:14:27.918148

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'ca05b4539457'
down_revision: Union[str, Sequence[str], None] = 'ac001aedae3f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


import json

# Копия данных на момент миграции: миграции не должны зависеть от кода приложения
TEMPLATES = {
    "excavator-loaders": ["Глубина копания", "Объём ковша экскаватора", "Объём ковша погрузчика",
                          "Высота выгрузки", "Грузоподъёмность", "Масса", "Мощность двигателя",
                          "Навесное оборудование"],
    "mini-excavators": ["Глубина копания", "Объём ковша", "Ширина", "Масса", "Мощность двигателя",
                        "Тип ходовой", "Навесное оборудование"],
    "crawler-excavators": ["Глубина копания", "Объём ковша", "Радиус копания", "Масса",
                           "Мощность двигателя", "Ширина гусениц", "Навесное оборудование"],
    "wheel-loaders": ["Объём ковша", "Грузоподъёмность", "Высота выгрузки", "Масса",
                      "Мощность двигателя", "Навесное оборудование"],
    "truck-cranes": ["Грузоподъёмность", "Длина стрелы", "Высота подъёма", "Вылет стрелы",
                     "Колёсная формула", "Гусёк"],
    "manipulators": ["Грузоподъёмность КМУ", "Вылет стрелы", "Грузоподъёмность борта", "Длина борта",
                     "Колёсная формула", "Люлька"],
    "dump-trucks": ["Грузоподъёмность", "Объём кузова", "Колёсная формула", "Тип разгрузки",
                    "Экологический класс"],
    "rollers": ["Масса", "Ширина вальца", "Тип вальца", "Вибрация", "Мощность двигателя"],
}

NEW_CATEGORIES = [
    ("Бульдозеры", "bulldozers",
     ["Масса", "Мощность двигателя", "Ширина отвала", "Тип отвала", "Рыхлитель"]),
    ("Автогрейдеры", "motor-graders",
     ["Масса", "Мощность двигателя", "Длина отвала", "Колёсная формула", "Рыхлитель"]),
    ("Мини-погрузчики", "skid-steer-loaders",
     ["Грузоподъёмность", "Объём ковша", "Высота выгрузки", "Масса", "Навесное оборудование"]),
    ("Телескопические погрузчики", "telehandlers",
     ["Грузоподъёмность", "Высота подъёма", "Вылет стрелы", "Масса", "Навесное оборудование"]),
    ("Автовышки", "aerial-platforms",
     ["Высота подъёма", "Вылет", "Грузоподъёмность люльки", "Тип стрелы", "Колёсная формула"]),
    ("Бетононасосы", "concrete-pumps",
     ["Длина стрелы", "Производительность", "Высота подачи", "Количество секций стрелы", "Базовое шасси"]),
    ("Ямобуры", "pile-drilling-rigs",
     ["Диаметр бурения", "Глубина бурения", "Базовое шасси", "Грузоподъёмность крана", "Вылет стрелы"]),
    ("Тралы и длинномеры", "low-bed-trailers",
     ["Грузоподъёмность", "Длина платформы", "Ширина платформы", "Высота погрузки", "Количество осей"]),
]

# Телефон к виду +7XXXXXXXXXX: 8 900 123-45-67, +7(900)1234567 и 9001234567 — один и тот же номер
DIGITS = "regexp_replace({col}, '\\D', '', 'g')"
NORMALIZED = (
    "CASE WHEN length({d}) = 11 AND left({d}, 1) IN ('7', '8') THEN '+7' || substr({d}, 2) "
    "WHEN length({d}) = 10 AND left({d}, 1) = '9' THEN '+7' || {d} ELSE {fallback} END"
)


def upgrade() -> None:
    # --- Категории: шаблоны характеристик и новые категории ---
    op.add_column(
        "categories",
        sa.Column("spec_template", postgresql.JSONB(astext_type=sa.Text()), server_default="[]", nullable=False),
    )
    for slug, names in TEMPLATES.items():
        op.execute(
            sa.text("UPDATE categories SET spec_template = CAST(:t AS jsonb) WHERE slug = :slug").bindparams(
                t=json.dumps(names, ensure_ascii=False), slug=slug
            )
        )
    for name, slug, names in NEW_CATEGORIES:
        op.execute(
            sa.text(
                "INSERT INTO categories (name, slug, spec_template) VALUES (:n, :s, CAST(:t AS jsonb)) "
                "ON CONFLICT (slug) DO NOTHING"
            ).bindparams(n=name, s=slug, t=json.dumps(names, ensure_ascii=False))
        )

    # --- Оператор теперь всегда включён: его стоимость переходит в цену техники ---
    op.execute(
        "UPDATE equipment SET "
        "price_per_hour = price_per_hour + COALESCE(operator_price_per_hour, 0), "
        "price_per_shift = price_per_shift + 8 * COALESCE(operator_price_per_hour, 0) "
        "WHERE operator_available"
    )
    op.drop_column("equipment", "operator_available")
    op.drop_column("equipment", "operator_price_per_hour")

    op.execute("UPDATE bookings SET rental_price = rental_price + operator_price")
    op.drop_column("bookings", "operator_price")
    op.drop_column("bookings", "with_operator")

    # --- Отзывы ---
    op.create_table(
        "reviews",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("booking_id", sa.Integer(), nullable=False),
        sa.Column("author_id", sa.Integer(), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("rating", sa.SmallInteger(), nullable=False),
        sa.Column("text", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("rating BETWEEN 1 AND 5", name=op.f("ck_reviews_rating_range")),
        sa.ForeignKeyConstraint(["author_id"], ["users.id"], name=op.f("fk_reviews_author_id_users"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["booking_id"], ["bookings.id"], name=op.f("fk_reviews_booking_id_bookings"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], name=op.f("fk_reviews_owner_id_users"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_reviews")),
        sa.UniqueConstraint("booking_id", name=op.f("uq_reviews_booking_id")),
    )
    op.create_index(op.f("ix_reviews_author_id"), "reviews", ["author_id"], unique=False)
    op.create_index(op.f("ix_reviews_owner_id"), "reviews", ["owner_id"], unique=False)

    # --- Телефоны к единому виду. Нераспознанный номер в профиле очищается, в брони остаётся как был ---
    d = DIGITS.format(col="phone")
    op.execute(f"UPDATE users SET phone = {NORMALIZED.format(d=d, fallback='NULL')} WHERE phone IS NOT NULL")
    d = DIGITS.format(col="contact_phone")
    op.execute(f"UPDATE bookings SET contact_phone = {NORMALIZED.format(d=d, fallback='contact_phone')}")


def downgrade() -> None:
    # Разделить цену обратно на технику и оператора невозможно: оператор остаётся внутри цены
    op.drop_index(op.f("ix_reviews_owner_id"), table_name="reviews")
    op.drop_index(op.f("ix_reviews_author_id"), table_name="reviews")
    op.drop_table("reviews")

    op.add_column(
        "bookings",
        sa.Column("with_operator", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    )
    op.add_column(
        "bookings",
        sa.Column("operator_price", sa.Numeric(12, 2), server_default=sa.text("'0'::numeric"), nullable=False),
    )
    op.add_column("equipment", sa.Column("operator_price_per_hour", sa.Numeric(10, 2), nullable=True))
    op.add_column(
        "equipment",
        sa.Column("operator_available", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    )

    op.execute(
        "DELETE FROM categories c WHERE slug = ANY(:slugs) AND NOT EXISTS "
        "(SELECT 1 FROM equipment e WHERE e.category_id = c.id)".replace(":slugs", "ARRAY[" + ",".join(
            f"'{slug}'" for _, slug, _ in NEW_CATEGORIES) + "]")
    )
    op.drop_column("categories", "spec_template")
