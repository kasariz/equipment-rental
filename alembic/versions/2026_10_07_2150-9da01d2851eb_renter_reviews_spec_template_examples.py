"""Отзывы об арендаторах; у характеристик в шаблонах категорий появились примеры значений

Revision ID: 9da01d2851eb
Revises: ca05b4539457
Create Date: 2026-10-07 21:50:38.470267

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9da01d2851eb'
down_revision: Union[str, Sequence[str], None] = 'ca05b4539457'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


import json

# Пример значения для каждой характеристики — в единицах, принятых для этой техники
EXAMPLES = {
    "excavator-loaders": {"Глубина копания": "5,9 м", "Объём ковша экскаватора": "0,2 м³",
                          "Объём ковша погрузчика": "1 м³", "Высота выгрузки": "2,7 м",
                          "Грузоподъёмность": "3 т", "Масса": "8,3 т", "Мощность двигателя": "100 л. с.",
                          "Навесное оборудование": "гидромолот, вилы"},
    "mini-excavators": {"Глубина копания": "2,8 м", "Объём ковша": "0,07 м³", "Ширина": "1,5 м", "Масса": "2,7 т",
                        "Мощность двигателя": "24 л. с.", "Тип ходовой": "гусеничная",
                        "Навесное оборудование": "гидробур, ковш-планировщик"},
    "crawler-excavators": {"Глубина копания": "6,6 м", "Объём ковша": "1 м³", "Радиус копания": "9,9 м",
                           "Масса": "21 т", "Мощность двигателя": "150 л. с.", "Ширина гусениц": "600 мм",
                           "Навесное оборудование": "гидромолот"},
    "wheel-loaders": {"Объём ковша": "1,8 м³", "Грузоподъёмность": "3 т", "Высота выгрузки": "3 м", "Масса": "10 т",
                      "Мощность двигателя": "125 л. с.", "Навесное оборудование": "вилы, щётка"},
    "truck-cranes": {"Грузоподъёмность": "25 т", "Длина стрелы": "21,7 м", "Высота подъёма": "22 м",
                     "Вылет стрелы": "18 м", "Колёсная формула": "6×4", "Гусёк": "9 м"},
    "manipulators": {"Грузоподъёмность КМУ": "7 т", "Вылет стрелы": "20 м", "Грузоподъёмность борта": "10 т",
                     "Длина борта": "6,2 м", "Колёсная формула": "6×6", "Люлька": "есть, на 2 человека"},
    "dump-trucks": {"Грузоподъёмность": "20 т", "Объём кузова": "16 м³", "Колёсная формула": "6×4",
                    "Тип разгрузки": "задняя", "Экологический класс": "Евро-5"},
    "rollers": {"Масса": "12 т", "Ширина вальца": "2,1 м", "Тип вальца": "гладкий", "Вибрация": "есть, 2 амплитуды",
                "Мощность двигателя": "130 л. с."},
    "bulldozers": {"Масса": "17 т", "Мощность двигателя": "180 л. с.", "Ширина отвала": "3,4 м",
                   "Тип отвала": "полуповоротный", "Рыхлитель": "есть, однозубый"},
    "motor-graders": {"Масса": "15 т", "Мощность двигателя": "180 л. с.", "Длина отвала": "3,7 м",
                      "Колёсная формула": "6×4", "Рыхлитель": "нет"},
    "skid-steer-loaders": {"Грузоподъёмность": "0,9 т", "Объём ковша": "0,4 м³", "Высота выгрузки": "2,4 м",
                           "Масса": "3 т", "Навесное оборудование": "бур, щётка, вилы"},
    "telehandlers": {"Грузоподъёмность": "4 т", "Высота подъёма": "17 м", "Вылет стрелы": "13 м", "Масса": "11 т",
                     "Навесное оборудование": "вилы, люлька"},
    "aerial-platforms": {"Высота подъёма": "22 м", "Вылет": "12 м", "Грузоподъёмность люльки": "250 кг",
                         "Тип стрелы": "телескопическая", "Колёсная формула": "4×2"},
    "concrete-pumps": {"Длина стрелы": "36 м", "Производительность": "150 м³/ч", "Высота подачи": "36 м",
                       "Количество секций стрелы": "4", "Базовое шасси": "КАМАЗ 6520"},
    "pile-drilling-rigs": {"Диаметр бурения": "200–800 мм", "Глубина бурения": "3 м",
                           "Базовое шасси": "КАМАЗ 43118", "Грузоподъёмность крана": "3 т", "Вылет стрелы": "7 м"},
    "low-bed-trailers": {"Грузоподъёмность": "40 т", "Длина платформы": "9 м", "Ширина платформы": "3 м",
                         "Высота погрузки": "0,9 м", "Количество осей": "3"},
}


def upgrade() -> None:
    # --- Шаблон характеристик: из списка названий в список {name, example} ---
    conn = op.get_bind()
    rows = conn.execute(sa.text("SELECT id, slug, spec_template FROM categories")).all()
    for cat_id, slug, template in rows:
        examples = EXAMPLES.get(slug, {})
        items = [
            item if isinstance(item, dict) else {"name": item, "example": examples.get(item)}
            for item in (template or [])
        ]
        conn.execute(
            sa.text("UPDATE categories SET spec_template = CAST(:t AS jsonb) WHERE id = :id"),
            {"t": json.dumps(items, ensure_ascii=False), "id": cat_id},
        )

    # --- Отзывы в обе стороны: о владельце (как раньше) и об арендаторе ---
    op.add_column(
        "reviews", sa.Column("direction", sa.String(16), server_default="about_owner", nullable=False)
    )
    op.create_check_constraint("direction_valid", "reviews", "direction IN ('about_owner', 'about_renter')")
    # owner_id → subject_id: теперь это тот, о ком отзыв, — владелец или арендатор
    op.alter_column("reviews", "owner_id", new_column_name="subject_id")
    op.execute("ALTER INDEX ix_reviews_owner_id RENAME TO ix_reviews_subject_id")
    op.execute("ALTER TABLE reviews RENAME CONSTRAINT fk_reviews_owner_id_users TO fk_reviews_subject_id_users")
    # По одной брони теперь два отзыва: клиента о владельце и владельца о клиенте
    op.drop_constraint(op.f("uq_reviews_booking_id"), "reviews", type_="unique")
    op.create_unique_constraint(op.f("uq_reviews_booking_id_direction"), "reviews", ["booking_id", "direction"])


def downgrade() -> None:
    op.execute("DELETE FROM reviews WHERE direction = 'about_renter'")
    op.drop_constraint(op.f("uq_reviews_booking_id_direction"), "reviews", type_="unique")
    op.create_unique_constraint(op.f("uq_reviews_booking_id"), "reviews", ["booking_id"])
    op.execute("ALTER TABLE reviews RENAME CONSTRAINT fk_reviews_subject_id_users TO fk_reviews_owner_id_users")
    op.execute("ALTER INDEX ix_reviews_subject_id RENAME TO ix_reviews_owner_id")
    op.alter_column("reviews", "subject_id", new_column_name="owner_id")
    op.drop_constraint(op.f("ck_reviews_direction_valid"), "reviews", type_="check")
    op.drop_column("reviews", "direction")

    conn = op.get_bind()
    for cat_id, template in conn.execute(sa.text("SELECT id, spec_template FROM categories")).all():
        names = [item["name"] if isinstance(item, dict) else item for item in (template or [])]
        conn.execute(
            sa.text("UPDATE categories SET spec_template = CAST(:t AS jsonb) WHERE id = :id"),
            {"t": json.dumps(names, ensure_ascii=False), "id": cat_id},
        )
