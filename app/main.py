import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI
from fastapi.routing import APIRoute
from fastapi.staticfiles import StaticFiles

from app.api.router import api_router
from app.core.config import settings
from app.services.booking_expiry import expiry_loop
from app.services.media import ensure_media_dirs
from app.services.telegram.bot import polling_loop


def generate_operation_id(route: APIRoute) -> str:
    # Короткие operationId в OpenAPI: "auth-login" вместо "login_api_auth_login_post"
    return f"{route.tags[0]}-{route.name}" if route.tags else route.name


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    ensure_media_dirs()
    tasks = [asyncio.create_task(expiry_loop()), asyncio.create_task(polling_loop())]
    yield
    for task in tasks:
        task.cancel()
    for task in tasks:
        with suppress(asyncio.CancelledError):
            await task


ensure_media_dirs()  # StaticFiles проверяет папку уже при создании приложения

app = FastAPI(
    title="Аренда спецтехники",
    version="0.5.0",
    generate_unique_id_function=generate_operation_id,
    lifespan=lifespan,
)
app.include_router(api_router)
# Загруженные фото. В продакшене их будет раздавать nginx или CDN
app.mount("/media", StaticFiles(directory=settings.media_dir), name="media")
