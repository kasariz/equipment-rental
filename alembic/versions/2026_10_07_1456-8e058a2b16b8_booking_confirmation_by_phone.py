"""booking confirmation by phone

Revision ID: 8e058a2b16b8
Revises: f66f4f46b5a8
Create Date: 2026-10-07 14:56:19.014891

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8e058a2b16b8'
down_revision: Union[str, Sequence[str], None] = 'f66f4f46b5a8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


OLD_WHERE = "status IN ('pending', 'paid', 'active')"
NEW_WHERE = "status IN ('pending', 'confirmed', 'active')"


def upgrade() -> None:
    """Подтверждение брони звонком: новые статусы, контакты и разбивка цены."""
    # Оплаты на сайте нет, вместо «оплачена» — «подтверждена владельцем».
    # Ограничение bookings_no_overlap хранит ссылку на значение enum, а не текст,
    # поэтому после переименования продолжает работать без пересоздания
    op.execute("ALTER TYPE booking_status RENAME VALUE 'paid' TO 'confirmed'")
    op.execute("ALTER TYPE booking_status ADD VALUE IF NOT EXISTS 'rejected'")
    op.execute("ALTER TYPE booking_status ADD VALUE IF NOT EXISTS 'expired'")

    op.add_column("bookings", sa.Column("rate_type", sa.String(16), server_default="hourly", nullable=False))
    op.add_column("bookings", sa.Column("quantity", sa.Integer(), server_default="1", nullable=False))
    op.add_column("bookings", sa.Column("contact_phone", sa.String(32), server_default="", nullable=False))
    op.alter_column("bookings", "contact_phone", server_default=None)
    op.add_column("bookings", sa.Column("comment", sa.Text(), nullable=True))
    op.add_column("bookings", sa.Column("reject_reason", sa.String(500), nullable=True))
    op.add_column("bookings", sa.Column("rental_price", sa.Numeric(12, 2), server_default="0", nullable=False))
    op.add_column("bookings", sa.Column("operator_price", sa.Numeric(12, 2), server_default="0", nullable=False))
    op.add_column(
        "bookings",
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_check_constraint("rate_type_valid", "bookings", "rate_type IN ('hourly', 'shift')")
    op.create_check_constraint("quantity_positive", "bookings", "quantity > 0")


def downgrade() -> None:
    op.drop_constraint(op.f("ck_bookings_quantity_positive"), "bookings", type_="check")
    op.drop_constraint(op.f("ck_bookings_rate_type_valid"), "bookings", type_="check")
    for column in ("updated_at", "operator_price", "rental_price", "reject_reason", "comment",
                   "contact_phone", "quantity", "rate_type"):
        op.drop_column("bookings", column)

    # Из enum в PostgreSQL нельзя удалить значение, поэтому пересоздаём тип целиком.
    # Ограничение зависит от типа колонки — снимаем его на время замены
    op.drop_constraint("bookings_no_overlap", "bookings")
    op.execute("UPDATE bookings SET status = 'cancelled' WHERE status IN ('rejected', 'expired')")
    op.execute("ALTER TYPE booking_status RENAME TO booking_status_new")
    op.execute(
        "CREATE TYPE booking_status AS ENUM ('pending', 'paid', 'active', 'completed', 'cancelled')"
    )
    op.execute("ALTER TABLE bookings ALTER COLUMN status DROP DEFAULT")
    op.execute(
        "ALTER TABLE bookings ALTER COLUMN status TYPE booking_status USING "
        "(CASE WHEN status::text = 'confirmed' THEN 'paid' ELSE status::text END)::booking_status"
    )
    op.execute("ALTER TABLE bookings ALTER COLUMN status SET DEFAULT 'pending'")
    op.execute("DROP TYPE booking_status_new")
    op.execute(
        f"ALTER TABLE bookings ADD CONSTRAINT bookings_no_overlap EXCLUDE USING gist "
        f"(equipment_id WITH =, period WITH &&) WHERE ({OLD_WHERE})"
    )
