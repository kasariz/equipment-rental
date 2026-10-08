"""Расчёт периода и цены аренды. Одна функция и для предпросмотра, и для создания брони,
поэтому цена в форме и в сохранённой заявке не может разойтись."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal

from app.models import Equipment, RateType

SHIFT_HOURS = 8
MAX_HOURS = 12
MAX_SHIFTS = 30


class PricingError(ValueError):
    pass


@dataclass(frozen=True)
class Quote:
    start: datetime
    end: datetime
    billable_hours: int
    total_price: Decimal


def shift_price(eq: Equipment) -> Decimal:
    # Если владелец не задал цену смены, считаем её как 8 часов
    return eq.price_per_shift if eq.price_per_shift is not None else eq.price_per_hour * SHIFT_HOURS


def calculate(eq: Equipment, rate_type: RateType, start: datetime, quantity: int) -> Quote:
    """Цены владельцев уже включают оператора: технику без машиниста не сдают"""
    if rate_type == RateType.hourly:
        if not eq.min_hours <= quantity <= MAX_HOURS:
            raise PricingError(f"Почасовая аренда: от {eq.min_hours} до {MAX_HOURS} часов")
        end = start + timedelta(hours=quantity)
        billable_hours = quantity
        rental = eq.price_per_hour * quantity
    else:
        if not 1 <= quantity <= MAX_SHIFTS:
            raise PricingError(f"Посменная аренда: от 1 до {MAX_SHIFTS} смен")
        # Смена в день: техника занята с начала первой смены до конца последней,
        # ночью она стоит на объекте клиента
        end = start + timedelta(days=quantity - 1, hours=SHIFT_HOURS)
        billable_hours = quantity * SHIFT_HOURS
        rental = shift_price(eq) * quantity

    return Quote(start=start, end=end, billable_hours=billable_hours, total_price=rental)
