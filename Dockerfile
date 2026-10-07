# Бэкенд: FastAPI + миграции при старте
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Зависимости отдельным слоем: при правке кода они не переустанавливаются
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY alembic.ini .
COPY alembic ./alembic
COPY app ./app

# Не от root: если в приложении найдут уязвимость, у атакующего будет меньше прав
RUN useradd --create-home --uid 1000 app && mkdir -p /app/media && chown app /app/media
USER app

EXPOSE 8000
# Один процесс: фоновые задачи (сгорание заявок, опрос Telegram) рассчитаны на одного исполнителя
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips '*'"]
