import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { api, getErrorMessage } from '@/api/client'
import type { operations } from '@/api/schema'

export type EquipmentQuery = NonNullable<operations['catalog-list_equipment']['parameters']['query']>

export function useCategories() {
  return useQuery({
    queryKey: ['categories'],
    queryFn: async () => {
      const { data, error } = await api.GET('/api/categories')
      if (!data) throw new Error(getErrorMessage(error))
      return data
    },
    staleTime: Infinity, // справочник почти не меняется
  })
}

export function useEquipmentList(query: EquipmentQuery) {
  return useQuery({
    queryKey: ['equipment', 'list', query],
    queryFn: async () => {
      const { data, error } = await api.GET('/api/equipment', { params: { query } })
      if (!data) throw new Error(getErrorMessage(error))
      return data
    },
    // Пока грузятся новые результаты, показываем старые, а не пустой экран
    placeholderData: keepPreviousData,
  })
}

export function useEquipment(id: number) {
  return useQuery({
    queryKey: ['equipment', 'detail', id],
    queryFn: async () => {
      const { data, error, response } = await api.GET('/api/equipment/{equipment_id}', {
        params: { path: { equipment_id: id } },
      })
      if (response.status === 404) return null
      if (!data) throw new Error(getErrorMessage(error))
      return data
    },
    enabled: Number.isFinite(id),
  })
}
