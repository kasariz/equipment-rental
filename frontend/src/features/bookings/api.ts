import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api, getErrorMessage, type BookingStatus } from '@/api/client'
import type { components } from '@/api/schema'

export type BookingParams = components['schemas']['BookingParams']
export type BookingCreateBody = components['schemas']['BookingCreate']

/** Ошибка API со статусом: форме важно отличать «время занято» (409) от остальных */
export class ApiError extends Error {
  status: number
  constructor(message: string, status: number) {
    super(message)
    this.status = status
  }
}

export function useBusy(equipmentId: number) {
  return useQuery({
    queryKey: ['bookings', 'busy', equipmentId],
    queryFn: async () => {
      const { data, error } = await api.GET('/api/equipment/{equipment_id}/busy', {
        params: { path: { equipment_id: equipmentId } },
      })
      if (!data) throw new Error(getErrorMessage(error))
      return data.map((i) => ({ start: new Date(i.start), end: new Date(i.end) }))
    },
    refetchInterval: 60_000, // занятость меняется, пока человек выбирает время
  })
}

export function useQuote(params: BookingParams | null) {
  return useQuery({
    queryKey: ['bookings', 'quote', params],
    queryFn: async () => {
      const { data, error, response } = await api.POST('/api/bookings/quote', { body: params! })
      if (!data) throw new ApiError(getErrorMessage(error), response.status)
      return data
    },
    enabled: params !== null,
    placeholderData: keepPreviousData,
    retry: false,
  })
}

function useInvalidateBookings() {
  const qc = useQueryClient()
  return () => qc.invalidateQueries({ queryKey: ['bookings'] })
}

export function useCreateBooking() {
  const invalidate = useInvalidateBookings()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (body: BookingCreateBody) => {
      const { data, error, response } = await api.POST('/api/bookings', { body })
      if (!data) throw new ApiError(getErrorMessage(error), response.status)
      return data
    },
    onSettled: () => {
      invalidate()
      qc.invalidateQueries({ queryKey: ['auth', 'me'] }) // телефон мог сохраниться в профиль
    },
  })
}

export function useMyBookings() {
  return useQuery({
    queryKey: ['bookings', 'my'],
    queryFn: async () => {
      const { data, error } = await api.GET('/api/my/bookings')
      if (!data) throw new Error(getErrorMessage(error))
      return data
    },
    refetchInterval: 60_000, // чтобы клиент увидел подтверждение без перезагрузки
  })
}

export function useCancelBooking() {
  const invalidate = useInvalidateBookings()
  return useMutation({
    mutationFn: async (id: number) => {
      const { data, error } = await api.POST('/api/bookings/{booking_id}/cancel', {
        params: { path: { booking_id: id } },
      })
      if (!data) throw new Error(getErrorMessage(error))
      return data
    },
    onSuccess: invalidate,
  })
}

export function useOwnerBookings(statuses?: BookingStatus[], options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: ['bookings', 'owner', statuses ?? 'all'],
    queryFn: async () => {
      const { data, error } = await api.GET('/api/owner/bookings', {
        params: { query: statuses ? { status: statuses } : {} },
      })
      if (!data) throw new Error(getErrorMessage(error))
      return data
    },
    refetchInterval: 30_000, // новые заявки появляются без перезагрузки страницы
    enabled: options?.enabled ?? true,
  })
}

type OwnerAction = 'confirm' | 'start' | 'complete'

export function useOwnerAction() {
  const invalidate = useInvalidateBookings()
  return useMutation({
    mutationFn: async ({ id, action }: { id: number; action: OwnerAction }) => {
      const path = { params: { path: { booking_id: id } } }
      const { data, error } =
        action === 'confirm'
          ? await api.POST('/api/bookings/{booking_id}/confirm', path)
          : action === 'start'
            ? await api.POST('/api/bookings/{booking_id}/start', path)
            : await api.POST('/api/bookings/{booking_id}/complete', path)
      if (!data) throw new Error(getErrorMessage(error))
      return data
    },
    onSuccess: invalidate,
  })
}

export function useRejectBooking() {
  const invalidate = useInvalidateBookings()
  return useMutation({
    mutationFn: async ({ id, reason }: { id: number; reason: string }) => {
      const { data, error } = await api.POST('/api/bookings/{booking_id}/reject', {
        params: { path: { booking_id: id } },
        body: { reason: reason.trim() || null },
      })
      if (!data) throw new Error(getErrorMessage(error))
      return data
    },
    onSuccess: invalidate,
  })
}
