import { useCallback, useMemo } from 'react'
import { useSearchParams } from 'react-router'
import type { EquipmentQuery } from './api'

export type CatalogFilters = {
  category: string
  q: string
  priceMax: string
  operator: boolean
  from: string // значение input datetime-local, без часового пояса
  to: string
  lat: string
  lon: string
  radius: string
  sort: NonNullable<EquipmentQuery['sort']>
}

const SORTS = ['new', 'price_asc', 'price_desc', 'distance'] as const

/**
 * Фильтры каталога живут в адресной строке: ссылкой на подборку можно поделиться,
 * а кнопка «Назад» в браузере возвращает к предыдущему поиску.
 */
export function useCatalogFilters() {
  const [params, setParams] = useSearchParams()

  const filters = useMemo<CatalogFilters>(() => {
    const sort = params.get('sort')
    return {
      category: params.get('category') ?? '',
      q: params.get('q') ?? '',
      priceMax: params.get('price_max') ?? '',
      operator: params.get('operator') === '1',
      from: params.get('from') ?? '',
      to: params.get('to') ?? '',
      lat: params.get('lat') ?? '',
      lon: params.get('lon') ?? '',
      radius: params.get('radius') ?? '',
      sort: SORTS.includes(sort as never) ? (sort as CatalogFilters['sort']) : 'new',
    }
  }, [params])

  const update = useCallback(
    (patch: Partial<CatalogFilters>) => {
      setParams(
        (prev) => {
          const next = new URLSearchParams(prev)
          const map: Record<keyof CatalogFilters, string> = {
            category: 'category', q: 'q', priceMax: 'price_max', operator: 'operator',
            from: 'from', to: 'to', lat: 'lat', lon: 'lon', radius: 'radius', sort: 'sort',
          }
          for (const [key, value] of Object.entries(patch) as [keyof CatalogFilters, unknown][]) {
            const str = typeof value === 'boolean' ? (value ? '1' : '') : String(value ?? '')
            if (str && !(key === 'sort' && str === 'new')) next.set(map[key], str)
            else next.delete(map[key])
          }
          return next
        },
        { replace: true },
      )
    },
    [setParams],
  )

  const reset = useCallback(() => setParams({}, { replace: true }), [setParams])

  // То же самое, но в формате запроса к API
  const query = useMemo<EquipmentQuery>(() => {
    const q: EquipmentQuery = { sort: filters.sort, limit: 200 }
    if (filters.category) q.category = filters.category
    if (filters.q.trim()) q.q = filters.q.trim()
    const price = Number(filters.priceMax)
    if (filters.priceMax && price > 0) q.price_max = price
    if (filters.operator) q.operator = true
    const hasPoint = filters.lat && filters.lon
    if (hasPoint) {
      q.lat = Number(filters.lat)
      q.lon = Number(filters.lon)
      if (filters.radius) q.radius_km = Number(filters.radius)
    } else if (q.sort === 'distance') {
      q.sort = 'new'
    }
    if (filters.from && filters.to) {
      const from = new Date(filters.from)
      const to = new Date(filters.to)
      if (from < to) {
        q.available_from = from.toISOString()
        q.available_to = to.toISOString()
      }
    }
    return q
  }, [filters])

  const activeCount =
    [filters.category, filters.q, filters.priceMax, filters.from && filters.to, filters.lat].filter(Boolean)
      .length + (filters.operator ? 1 : 0)

  return { filters, update, reset, query, activeCount }
}
