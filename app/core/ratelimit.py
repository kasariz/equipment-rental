"""Ограничение частоты запросов: защита от перебора паролей и спама.

Счётчики живут в памяти процесса. Для одного сервера этого достаточно; если серверов станет
несколько, счётчики нужно перенести в Redis, интерфейс останется тем же.
"""

import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request, status

from app.core.config import settings


class RateLimiter:
    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def hit(self, key: str, limit: int, window_seconds: int) -> None:
        """Засчитывает попытку. Если их больше limit за окно — 429 с подсказкой, сколько ждать"""
        if not settings.rate_limit_enabled:
            return
        now = time.monotonic()
        hits = self._hits[key]
        while hits and hits[0] <= now - window_seconds:
            hits.popleft()
        if len(hits) >= limit:
            retry_after = int(hits[0] + window_seconds - now) + 1
            minutes = max(1, round(retry_after / 60))
            raise HTTPException(
                status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Слишком много попыток. Попробуйте через {minutes} мин.",
                headers={"Retry-After": str(retry_after)},
            )
        hits.append(now)

    def reset(self) -> None:
        self._hits.clear()


limiter = RateLimiter()


def client_ip(request: Request) -> str:
    # За Caddy uvicorn запущен с --proxy-headers, поэтому здесь настоящий адрес посетителя
    return request.client.host if request.client else "unknown"
