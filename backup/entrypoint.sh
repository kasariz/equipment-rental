#!/bin/sh
# Запускает копирование по расписанию через crond.
# crond не передаёт заданиям переменные окружения контейнера, поэтому сохраняем их в файл,
# который backup.sh подключает перед работой.
set -eu

export -p > /scripts/env.sh
SCHEDULE="${BACKUP_SCHEDULE:-0 0 * * *}"  # время в UTC: 00:00 UTC = 03:00 по Москве
echo "$SCHEDULE /scripts/backup.sh >> /proc/1/fd/1 2>&1" > /etc/crontabs/root

echo "Резервное копирование: расписание «$SCHEDULE» (UTC), папка /backups, хранить ${KEEP_DAYS:-14} дн."
exec crond -f -l 8
