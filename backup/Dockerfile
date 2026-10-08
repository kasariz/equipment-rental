# Резервное копирование: та же версия PostgreSQL, что у базы, — pg_dump должен ей соответствовать
FROM postgres:16-alpine

# curl — для сообщений в Telegram (во встроенном wget нет поддержки HTTPS)
RUN apk add --no-cache curl

COPY entrypoint.sh backup.sh restore.sh /scripts/
# Права на запуск выставляем здесь: из Windows атрибут «исполняемый» не переносится
RUN chmod +x /scripts/*.sh

ENTRYPOINT ["/scripts/entrypoint.sh"]
