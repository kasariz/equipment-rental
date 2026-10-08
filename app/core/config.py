from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEV_SECRET = "dev-secret-change-me-please-32-bytes-min"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: Literal["development", "production"] = "development"

    postgres_user: str = "rental"
    postgres_password: str = "rental"
    postgres_db: str = "rental"
    postgres_host: str = "localhost"
    postgres_port: int = 5432

    # Ключ для подписи JWT. Для разработки есть значение по умолчанию,
    # в продакшене обязательно задать свой в .env
    secret_key: str = DEV_SECRET
    access_token_expire_minutes: int = 60 * 24 * 7  # неделя
    # В разработке сайт работает по http, поэтому secure-cookie выключены
    cookie_secure: bool = False

    # Куда складывать загруженные фото. В продакшене — volume или S3
    media_dir: str = "media"
    max_photo_size_mb: int = 10
    max_photos_per_equipment: int = 10

    # Бронирование
    booking_min_lead_hours: int = 2  # за сколько часов до начала можно оставить заявку
    booking_max_days_ahead: int = 90
    booking_pending_ttl_hours: int = 24  # сколько ждём звонка владельца, потом заявка сгорает

    # Telegram-уведомления. Без токена сайт работает, просто ничего не отправляет
    telegram_bot_token: str = ""
    telegram_api_base: str = "https://api.telegram.org"  # в тестах подменяется на фейковый сервер
    # В этом часовом поясе время пишется в уведомлениях
    timezone: str = "Europe/Moscow"
    # Ключ «API Геокодера» Яндекса: подсказки адресов. Без него адрес вводится свободным текстом
    yandex_geocoder_api_key: str = ""
    yandex_geocoder_url: str = "https://geocode-maps.yandex.ru/v1/"

    # Адрес сайта для кнопок в сообщениях. Telegram не принимает ссылки на localhost,
    # поэтому с локальным адресом кнопки просто не добавляются
    site_url: str = "http://localhost:5173"

    @model_validator(mode="after")
    def check_production(self) -> "Settings":
        # Сервер с ключом из репозитория — это сервер, где любой может подделать вход
        if self.environment == "production" and (self.secret_key == DEV_SECRET or len(self.secret_key) < 32):
            raise ValueError("В production задайте свой SECRET_KEY длиной от 32 символов")
        return self

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


settings = Settings()
