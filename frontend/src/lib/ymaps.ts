import type { LngLat, LngLatBounds } from '@yandex/ymaps3-types'
import * as React from 'react'
import * as ReactDOM from 'react-dom'
import { useEffect, useState } from 'react'

/**
 * Яндекс Карты JS API v3. Скрипт грузится один раз и только на страницах с картой,
 * а компоненты карты оборачиваются в React через официальный модуль reactify.
 */

const API_KEY = import.meta.env.VITE_YANDEX_MAPS_API_KEY

export const DEFAULT_CENTER: LngLat = [39.7015, 47.2357] // Ростов-на-Дону. Внимание: сначала долгота!
export const DEFAULT_ZOOM = 11

function loadScript(src: string): Promise<void> {
  return new Promise((resolve, reject) => {
    const script = document.createElement('script')
    script.src = src
    script.async = true
    script.onload = () => resolve()
    script.onerror = () =>
      reject(
        new Error(
          'Не удалось загрузить Яндекс Карты. Чаще всего причина в ключе: он ещё не активен ' +
            'или сайт не указан в ограничениях по HTTP Referer. Также карту может блокировать блокировщик рекламы',
        ),
      )
    document.head.append(script)
  })
}

async function loadYMaps() {
  if (!API_KEY) {
    throw new Error('Не задан ключ Яндекс Карт: добавьте VITE_YANDEX_MAPS_API_KEY в frontend/.env.local')
  }
  await loadScript(`https://api-maps.yandex.ru/v3/?apikey=${encodeURIComponent(API_KEY)}&lang=ru_RU`)
  const [ymaps3React] = await Promise.all([ymaps3.import('@yandex/ymaps3-reactify'), ymaps3.ready])
  const reactify = ymaps3React.reactify.bindTo(React, ReactDOM)
  return reactify.module(ymaps3)
}

export type YMapsComponents = Awaited<ReturnType<typeof loadYMaps>>

let loading: Promise<YMapsComponents> | null = null

/** Компоненты карты или ошибка загрузки. Пока грузится, оба поля пустые */
export function useYMaps(): { ymaps?: YMapsComponents; error?: Error } {
  const [state, setState] = useState<{ ymaps?: YMapsComponents; error?: Error }>({})
  useEffect(() => {
    let alive = true
    loading ??= loadYMaps().catch((e: unknown) => {
      loading = null // чтобы при следующем открытии карты попробовать снова
      throw e
    })
    loading.then(
      (ymaps) => alive && setState({ ymaps }),
      (error: Error) => alive && setState({ error }),
    )
    return () => {
      alive = false
    }
  }, [])
  return state
}

/** Наши данные хранят [широта, долгота], а Яндекс ждёт [долгота, широта] */
export function toLngLat(lat: number, lon: number): LngLat {
  return [lon, lat]
}

/** Границы, в которые помещаются все точки, с небольшим отступом по краям */
export function boundsFor(points: LngLat[]): LngLatBounds {
  const lons = points.map((p) => p[0])
  const lats = points.map((p) => p[1])
  const [minLon, maxLon, minLat, maxLat] = [Math.min(...lons), Math.max(...lons), Math.min(...lats), Math.max(...lats)]
  const padLon = Math.max((maxLon - minLon) * 0.15, 0.01)
  const padLat = Math.max((maxLat - minLat) * 0.15, 0.01)
  // Яндекс ждёт [левый верхний угол, правый нижний]
  return [
    [minLon - padLon, maxLat + padLat],
    [maxLon + padLon, minLat - padLat],
  ]
}

export function boundsContain(bounds: LngLatBounds, point: LngLat): boolean {
  const [[left, top], [right, bottom]] = bounds
  return point[0] >= left && point[0] <= right && point[1] >= bottom && point[1] <= top
}
