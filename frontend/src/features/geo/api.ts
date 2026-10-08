import { useQuery } from '@tanstack/react-query'
import { api, getErrorMessage } from '@/api/client'
import type { components } from '@/api/schema'

export type GeoSuggestion = components['schemas']['GeoSuggestion']

/** Адрес, выбранный из подсказок геокодера. token — подпись сервера, без неё адрес не примут */
export type PickedAddress = { address: string; token: string | null; lat?: number; lon?: number }

export function useGeoStatus() {
  return useQuery({
    queryKey: ['geo', 'status'],
    queryFn: async () => {
      const { data } = await api.GET('/api/geo/status')
      return data ?? { enabled: false }
    },
    staleTime: Infinity,
  })
}

export async function searchAddress(q: string): Promise<GeoSuggestion[]> {
  const { data, error } = await api.GET('/api/geo/search', { params: { query: { q } } })
  if (!data) throw new Error(getErrorMessage(error))
  return data
}

export async function reverseGeocode(lat: number, lon: number): Promise<GeoSuggestion | null> {
  const { data, error, response } = await api.GET('/api/geo/reverse', { params: { query: { lat, lon } } })
  if (!response.ok) throw new Error(getErrorMessage(error))
  return data ?? null
}
