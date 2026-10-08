from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from app.models import Equipment, RateType
from app.services.pricing import PricingError, calculate

START = datetime(2030, 5, 20, 6, 0, tzinfo=UTC)


def make(**kw) -> Equipment:
    defaults = {"price_per_hour": Decimal(3100), "price_per_shift": Decimal(22800), "min_hours": 4}
    return Equipment(**(defaults | kw))


def test_hourly():
    q = calculate(make(), RateType.hourly, START, 5)
    assert q.end == START + timedelta(hours=5)
    assert q.total_price == 15500


def test_shifts_block_whole_days_and_bill_eight_hours_each():
    q = calculate(make(), RateType.shift, START, 3)
    # Первая смена 8 ч, между сменами техника остаётся на объекте
    assert q.end == START + timedelta(days=2, hours=8)
    assert q.billable_hours == 24
    assert q.total_price == 3 * 22800


def test_shift_price_defaults_to_eight_hours():
    q = calculate(make(price_per_shift=None), RateType.shift, START, 1)
    assert q.total_price == 8 * 3100


@pytest.mark.parametrize("hours", [3, 13])
def test_hourly_limits(hours: int):
    with pytest.raises(PricingError, match="от 4 до 12"):
        calculate(make(), RateType.hourly, START, hours)
