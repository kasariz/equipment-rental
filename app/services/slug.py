import re

TRANSLIT = dict(
    zip(
        "абвгдеёжзийклмнопрстуфхцчшщъыьэюя",
        [
            "a",
            "b",
            "v",
            "g",
            "d",
            "e",
            "e",
            "zh",
            "z",
            "i",
            "y",
            "k",
            "l",
            "m",
            "n",
            "o",
            "p",
            "r",
            "s",
            "t",
            "u",
            "f",
            "h",
            "ts",
            "ch",
            "sh",
            "sch",
            "",
            "y",
            "",
            "e",
            "yu",
            "ya",
        ],
        strict=True,
    )
)


def slugify(text: str) -> str:
    """«Бетоносмесители» → «betonosmesiteli»: для адресов вида /catalog?category=…"""
    latin = "".join(TRANSLIT.get(ch, ch) for ch in text.lower())
    return re.sub(r"[^a-z0-9]+", "-", latin).strip("-") or "category"
