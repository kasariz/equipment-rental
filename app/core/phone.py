"""Российские телефоны в едином виде +7XXXXXXXXXX.

8 900 123-45-67, +7 (900) 123-45-67 и 9001234567 — один и тот же номер.
"""

import re
from typing import Annotated

from pydantic import AfterValidator, Field


def normalize_phone(value: str) -> str:
    digits = re.sub(r"\D", "", value)
    if len(digits) == 11 and digits[0] in "78":
        national = digits[1:]
    elif len(digits) == 10:
        national = digits
    else:
        raise ValueError("Введите номер в формате +7 (900) 123-45-67")
    # Коды в России начинаются с 3, 4, 8 (городские) или 9 (мобильные)
    if national[0] not in "3489":
        raise ValueError("Такого кода в российских номерах нет")
    # Кодов 89x нет: «8 900 123 45 6» — это мобильный, в котором не хватает цифры
    if national.startswith("89"):
        raise ValueError("В номере не хватает цифры")
    return "+7" + national


def format_phone(phone: str) -> str:
    """+79001234567 → +7 (900) 123-45-67. Старые номера в другом виде возвращаются как есть"""
    if re.fullmatch(r"\+7\d{10}", phone):
        d = phone[2:]
        return f"+7 ({d[:3]}) {d[3:6]}-{d[6:8]}-{d[8:]}"
    return phone


Phone = Annotated[str, Field(max_length=32), AfterValidator(normalize_phone)]
