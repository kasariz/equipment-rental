"""Создать администратора или сделать администратором существующего пользователя.

Локально:  python -m app.scripts.create_admin admin@example.ru
В Docker:  docker compose -f docker-compose.prod.yml --env-file .env.prod exec backend \\
               python -m app.scripts.create_admin admin@example.ru
"""

import argparse
import asyncio
import getpass

from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models import User, UserRole


async def promote(email: str) -> bool:
    """Если пользователь уже есть, делает его администратором и возвращает True"""
    async with SessionLocal() as session:
        user = await session.scalar(select(User).where(User.email == email))
        if user is None:
            return False
        user.role = UserRole.admin
        await session.commit()
        return True


async def create(email: str, name: str, password: str) -> None:
    async with SessionLocal() as session:
        session.add(User(email=email, hashed_password=hash_password(password), full_name=name, role=UserRole.admin))
        await session.commit()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("email")
    email = parser.parse_args().email.strip().lower()

    if asyncio.run(promote(email)):
        print(f"{email} теперь администратор")
        return

    # Ввод с клавиатуры — до запуска асинхронного кода: input() блокирует цикл событий
    name = input("Имя администратора: ").strip() or "Администратор"
    password = getpass.getpass("Пароль (не меньше 8 символов): ")
    if len(password) < 8:
        raise SystemExit("Пароль слишком короткий")
    if password != getpass.getpass("Повторите пароль: "):
        raise SystemExit("Пароли не совпадают")
    asyncio.run(create(email, name, password))
    print(f"Администратор {email} создан")


if __name__ == "__main__":
    main()
