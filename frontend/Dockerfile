# 1. Сборка фронтенда
FROM node:22-alpine AS build
WORKDIR /src
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
# Ключ карт попадает в собранный JavaScript: в браузере он виден всё равно
ARG VITE_YANDEX_MAPS_API_KEY=""
ENV VITE_YANDEX_MAPS_API_KEY=$VITE_YANDEX_MAPS_API_KEY
RUN npm run build

# 2. Caddy раздаёт фронтенд и фото, проксирует API и сам получает HTTPS-сертификат
FROM caddy:2.11-alpine
COPY Caddyfile /etc/caddy/Caddyfile
COPY --from=build /src/dist /srv/app
