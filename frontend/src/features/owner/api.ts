import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api, getErrorMessage, type Photo } from '@/api/client'
import type { components } from '@/api/schema'

export type EquipmentCreateBody = components['schemas']['EquipmentCreate']
export type EquipmentUpdateBody = components['schemas']['EquipmentUpdate']

const myKey = ['equipment', 'my'] as const

export function useMyEquipment() {
  return useQuery({
    queryKey: myKey,
    queryFn: async () => {
      const { data, error } = await api.GET('/api/my/equipment')
      if (!data) throw new Error(getErrorMessage(error))
      return data
    },
  })
}

/** После любых изменений техники сбрасываем и каталог, и кабинет */
function useInvalidateEquipment() {
  const qc = useQueryClient()
  return () => qc.invalidateQueries({ queryKey: ['equipment'] })
}

export function useCreateEquipment() {
  const invalidate = useInvalidateEquipment()
  return useMutation({
    mutationFn: async (body: EquipmentCreateBody) => {
      const { data, error } = await api.POST('/api/equipment', { body })
      if (!data) throw new Error(getErrorMessage(error))
      return data
    },
    onSuccess: invalidate,
  })
}

export function useUpdateEquipment(id: number) {
  const invalidate = useInvalidateEquipment()
  return useMutation({
    mutationFn: async (body: EquipmentUpdateBody) => {
      const { data, error } = await api.PATCH('/api/equipment/{equipment_id}', {
        params: { path: { equipment_id: id } },
        body,
      })
      if (!data) throw new Error(getErrorMessage(error))
      return data
    },
    onSuccess: invalidate,
  })
}

export function useDeleteEquipment() {
  const invalidate = useInvalidateEquipment()
  return useMutation({
    mutationFn: async (id: number) => {
      const { error, response } = await api.DELETE('/api/equipment/{equipment_id}', {
        params: { path: { equipment_id: id } },
      })
      if (!response.ok) throw new Error(getErrorMessage(error))
    },
    onSuccess: invalidate,
  })
}

/** Загрузка фото. Обычный fetch, потому что тело — multipart/form-data */
export async function uploadPhotos(equipmentId: number, files: File[]): Promise<Photo[]> {
  const form = new FormData()
  files.forEach((file) => form.append('files', file))
  const response = await fetch(`/api/equipment/${equipmentId}/photos`, { method: 'POST', body: form })
  const data = await response.json().catch(() => null)
  if (!response.ok) throw new Error(getErrorMessage(data, 'Не удалось загрузить фото'))
  return data as Photo[]
}

export async function deletePhoto(equipmentId: number, photoId: number): Promise<void> {
  const { error, response } = await api.DELETE('/api/equipment/{equipment_id}/photos/{photo_id}', {
    params: { path: { equipment_id: equipmentId, photo_id: photoId } },
  })
  if (!response.ok) throw new Error(getErrorMessage(error, 'Не удалось удалить фото'))
}
