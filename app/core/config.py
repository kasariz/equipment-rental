from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    postgres_user: str = "rental"
    postgres_password: str = "rental"
    postgres_db: str = "rental"
    postgres_host: str = "localhost"
    postgres_port: int = 5432

    # Ключ для подписи JWT. Для разработки есть значение по умолчанию,
    # в продакшене обязательно задать свой в .env
    secret_key: str = "dev-secret-change-me-please-32-bytes-min"
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

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


settings = Settings()
