import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api, getErrorMessage } from '@/api/client'

export function useFavorites(enabled = true) {
  return useQuery({
    queryKey: ['equipment', 'favorites'],
    queryFn: async () => {
      const { data, error } = await api.GET('/api/my/favorites')
      if (!data) throw new Error(getErrorMessage(error))
      return data
    },
    enabled,
  })
}

export function useToggleFavorite() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async ({ id, favorite }: { id: number; favorite: boolean }) => {
      const path = { params: { path: { equipment_id: id } } }
      const { error, response } = favorite
        ? await api.PUT('/api/favorites/{equipment_id}', path)
        : await api.DELETE('/api/favorites/{equipment_id}', path)
      if (!response.ok) throw new Error(getErrorMessage(error))
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['equipment'] }),
  })
}

export function useSimilar(id: number) {
  return useQuery({
    queryKey: ['equipment', 'similar', id],
    queryFn: async () => {
      const { data, error } = await api.GET('/api/equipment/{equipment_id}/similar', {
        params: { path: { equipment_id: id } },
      })
      if (!data) throw new Error(getErrorMessage(error))
      return data
    },
  })
}
