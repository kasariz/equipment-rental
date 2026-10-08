#!/bin/sh
# Восстановление из копии. ВНИМАНИЕ: текущие данные базы заменяются данными из копии.
#   docker compose -f docker-compose.prod.yml --env-file .env.prod exec backup /scripts/restore.sh db_2026-10-08_00-00.dump
# Без имени файла — показывает список доступных копий.
set -eu
[ -f /scripts/env.sh ] && . /scripts/env.sh

BACKUP_DIR="${BACKUP_DIR:-/backups}"
MEDIA_DIR="${MEDIA_DIR:-/media}"
export PGPASSWORD="$POSTGRES_PASSWORD"

if [ $# -eq 0 ]; then
    echo "Доступные копии (новые внизу):"
    ls -1 "$BACKUP_DIR" | grep '^db_.*\.dump$' || echo "  копий нет"
    echo "Восстановить: restore.sh <имя файла db_….dump>"
    exit 0
fi

DB_FILE="$BACKUP_DIR/$1"
[ -f "$DB_FILE" ] || { echo "Нет файла $DB_FILE"; exit 1; }
MEDIA_FILE="$BACKUP_DIR/$(echo "$1" | sed 's/^db_/media_/; s/\.dump$/.tar.gz/')"

echo "Восстанавливаю базу из $1 …"
# --clean --if-exists: удалить текущие таблицы перед восстановлением; одна транзакция — всё или ничего
pg_restore -h "${POSTGRES_HOST:-db}" -p "${POSTGRES_PORT:-5432}" -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
    --clean --if-exists --no-owner --single-transaction "$DB_FILE"

if [ -f "$MEDIA_FILE" ] && [ -d "$MEDIA_DIR" ]; then
    echo "Восстанавливаю фото из $(basename "$MEDIA_FILE") …"
    find "$MEDIA_DIR" -mindepth 1 -delete
    tar -xzf "$MEDIA_FILE" -C "$MEDIA_DIR"
fi
echo "Готово. Перезапустите бэкенд, чтобы он подхватил данные."
