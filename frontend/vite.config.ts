import path from 'node:path'
import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: { '@': path.resolve(import.meta.dirname, './src') },
  },
  server: {
    // Явно слушаем IPv4: на Windows "localhost" иногда резолвится только в ::1,
    // и браузер получает ERR_CONNECTION_REFUSED
    host: '127.0.0.1',
    port: 5173,
    strictPort: true,
    // Запросы /api/* фронт отправляет на свой же адрес, а Vite пересылает их в FastAPI.
    // Браузер видит один источник: не нужен CORS, и httpOnly-cookie работают без настроек.
    proxy: {
      '/api': 'http://127.0.0.1:8000',
      '/media': 'http://127.0.0.1:8000',
    },
  },
})
