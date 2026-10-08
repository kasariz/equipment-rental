import pytest

from app.core.phone import format_phone, normalize_phone


@pytest.mark.parametrize(
    "raw", ["8 900 123-45-67", "+7 (900) 123-45-67", "89001234567", "79001234567", "9001234567", " +7-900-123-4567 "]
)
def test_all_forms_give_the_same_number(raw: str):
    assert normalize_phone(raw) == "+79001234567"


def test_landline():
    assert normalize_phone("8 (863) 200-00-00") == "+78632000000"


@pytest.mark.parametrize("raw", ["12345", "+1 212 555 0100", "8 900 123 45 6", "8 900 123 45 678 9", "8 100 123 45 67"])
def test_invalid(raw: str):
    with pytest.raises(ValueError):
        normalize_phone(raw)


def test_format():
    assert format_phone("+79001234567") == "+7 (900) 123-45-67"
    assert format_phone("старый номер") == "старый номер"
