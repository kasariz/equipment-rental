#!/bin/sh
# Одна резервная копия: дамп базы + архив фото. Ручной запуск:
#   docker compose -f docker-compose.prod.yml --env-file .env.prod exec backup /scripts/backup.sh
set -eu
[ -f /scripts/env.sh ] && . /scripts/env.sh

BACKUP_DIR="${BACKUP_DIR:-/backups}"
MEDIA_DIR="${MEDIA_DIR:-/media}"
KEEP_DAYS="${KEEP_DAYS:-14}"
STAMP="$(date +%Y-%m-%d_%H-%M)"
DB_FILE="$BACKUP_DIR/db_$STAMP.dump"
MEDIA_FILE="$BACKUP_DIR/media_$STAMP.tar.gz"
export PGPASSWORD="$POSTGRES_PASSWORD"

notify() {
    # Тихо пропускаем, если бот мониторинга не настроен
    [ -n "${ALERT_BOT_TOKEN:-}" ] && [ -n "${ALERT_CHAT_ID:-}" ] || return 0
    curl -s -m 15 "https://api.telegram.org/bot$ALERT_BOT_TOKEN/sendMessage" \
        -d chat_id="$ALERT_CHAT_ID" --data-urlencode text="$1" > /dev/null || true
}

fail() {
    echo "ОШИБКА: $1"
    rm -f "$DB_FILE.tmp" "$MEDIA_FILE.tmp"
    notify "🔴 Резервная копия «Ковш» не сделана: $1"
    exit 1
}

mkdir -p "$BACKUP_DIR" || fail "нет доступа к папке копий $BACKUP_DIR"

# Пишем во временный файл и переименовываем в конце: недописанная копия никогда не выглядит готовой
pg_dump -h "${POSTGRES_HOST:-db}" -p "${POSTGRES_PORT:-5432}" -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
    --format=custom --file="$DB_FILE.tmp" || fail "pg_dump завершился с ошибкой"
# Проверяем, что копию можно прочитать: битый дамп хуже, чем никакого
pg_restore --list "$DB_FILE.tmp" > /dev/null || fail "копия базы не читается"
mv "$DB_FILE.tmp" "$DB_FILE"

if [ -d "$MEDIA_DIR" ]; then
    tar -czf "$MEDIA_FILE.tmp" -C "$MEDIA_DIR" . || fail "не удалось заархивировать фото"
    mv "$MEDIA_FILE.tmp" "$MEDIA_FILE"
fi

# Удаляем копии старше KEEP_DAYS дней, но никогда не трогаем только что сделанную
find "$BACKUP_DIR" -maxdepth 1 \( -name 'db_*.dump' -o -name 'media_*.tar.gz' \) -mtime +"$KEEP_DAYS" -delete

DB_SIZE="$(du -h "$DB_FILE" | cut -f1)"
COUNT="$(find "$BACKUP_DIR" -maxdepth 1 -name 'db_*.dump' | wc -l | tr -d ' ')"
echo "Готово: $DB_FILE ($DB_SIZE), всего копий базы: $COUNT"
if [ "${BACKUP_NOTIFY_SUCCESS:-false}" = "true" ]; then
    notify "✅ Резервная копия «Ковш»: база $DB_SIZE, всего копий: $COUNT"
fi
