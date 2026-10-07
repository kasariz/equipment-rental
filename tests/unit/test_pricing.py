from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from app.models import Equipment, RateType
from app.services.pricing import PricingError, calculate

START = datetime(2030, 5, 20, 6, 0, tzinfo=UTC)


def make(**kw) -> Equipment:
    defaults = {
        "price_per_hour": Decimal(2500),
        "price_per_shift": Decimal(18000),
        "min_hours": 4,
        "operator_available": True,
        "operator_price_per_hour": Decimal(600),
    }
    return Equipment(**(defaults | kw))


def test_hourly_with_operator():
    q = calculate(make(), RateType.hourly, START, 5, with_operator=True)
    assert q.end == START + timedelta(hours=5)
    assert (q.rental_price, q.operator_price, q.total_price) == (12500, 3000, 15500)


def test_shifts_block_whole_days_and_bill_eight_hours_each():
    q = calculate(make(), RateType.shift, START, 3, with_operator=True)
    # Первая смена 8 ч, между сменами техника остаётся на объекте
    assert q.end == START + timedelta(days=2, hours=8)
    assert q.billable_hours == 24
    assert q.rental_price == 54000
    assert q.operator_price == 24 * 600


def test_shift_price_defaults_to_eight_hours():
    q = calculate(make(price_per_shift=None), RateType.shift, START, 1, with_operator=False)
    assert q.total_price == 8 * 2500


@pytest.mark.parametrize("hours", [3, 13])
def test_hourly_limits(hours: int):
    with pytest.raises(PricingError, match="от 4 до 12"):
        calculate(make(), RateType.hourly, START, hours, with_operator=False)


def test_operator_not_offered():
    with pytest.raises(PricingError, match="оператора"):
        calculate(make(operator_available=False), RateType.hourly, START, 4, with_operator=True)
