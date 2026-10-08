import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api, getErrorMessage } from '@/api/client'

export function useCalendar(equipmentId: number, from: string, to: string) {
  return useQuery({
    queryKey: ['bookings', 'calendar', equipmentId, from, to],
    queryFn: async () => {
      const { data, error } = await api.GET('/api/equipment/{equipment_id}/calendar', {
        params: { path: { equipment_id: equipmentId }, query: { from, to } },
      })
      if (!data) throw new Error(getErrorMessage(error))
      return data.map((i) => ({ ...i, startDate: new Date(i.start), endDate: new Date(i.end) }))
    },
  })
}

export function useCreateBlock(equipmentId: number) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (body: { start: string; end: string; reason: string | null }) => {
      const { data, error } = await api.POST('/api/equipment/{equipment_id}/blocks', {
        params: { path: { equipment_id: equipmentId } },
        body,
      })
      if (!data) throw new Error(getErrorMessage(error))
      return data
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['bookings'] }),
  })
}

export function useDeleteBlock(equipmentId: number) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (blockId: number) => {
      const { error, response } = await api.DELETE('/api/equipment/{equipment_id}/blocks/{block_id}', {
        params: { path: { equipment_id: equipmentId, block_id: blockId } },
      })
      if (!response.ok) throw new Error(getErrorMessage(error))
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['bookings'] }),
  })
}
