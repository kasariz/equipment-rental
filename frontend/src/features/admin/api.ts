import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api, getErrorMessage } from '@/api/client'
import type { operations } from '@/api/schema'

type Query<Op extends keyof operations> = NonNullable<operations[Op]['parameters']['query']>
export type UsersQuery = Query<'admin-list_users'>
export type EquipmentQuery = Query<'admin-list_equipment'>
export type BookingsQuery = Query<'admin-list_bookings'>
export type ReviewsQuery = Query<'admin-list_reviews'>

// Пока грузится следующая страница или новый фильтр, показываем прежние данные, а не пустоту
const listOptions = { placeholderData: keepPreviousData } as const

export function useAdminUsers(query: UsersQuery) {
  return useQuery({
    queryKey: ['admin', 'users', query],
    queryFn: async () => {
      const { data, error } = await api.GET('/api/admin/users', { params: { query } })
      if (!data) throw new Error(getErrorMessage(error))
      return data
    },
    ...listOptions,
  })
}

export function useAdminEquipment(query: EquipmentQuery) {
  return useQuery({
    queryKey: ['admin', 'equipment', query],
    queryFn: async () => {
      const { data, error } = await api.GET('/api/admin/equipment', { params: { query } })
      if (!data) throw new Error(getErrorMessage(error))
      return data
    },
    ...listOptions,
  })
}

export function useAdminBookings(query: BookingsQuery) {
  return useQuery({
    queryKey: ['admin', 'bookings', query],
    queryFn: async () => {
      const { data, error } = await api.GET('/api/admin/bookings', { params: { query } })
      if (!data) throw new Error(getErrorMessage(error))
      return data
    },
    ...listOptions,
  })
}

export function useAdminReviews(query: ReviewsQuery) {
  return useQuery({
    queryKey: ['admin', 'reviews', query],
    queryFn: async () => {
      const { data, error } = await api.GET('/api/admin/reviews', { params: { query } })
      if (!data) throw new Error(getErrorMessage(error))
      return data
    },
    ...listOptions,
  })
}

type Entity = 'users' | 'equipment' | 'bookings' | 'reviews' | 'categories'

export function useAdminDelete(entity: Entity) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (id: number) => {
      const call = {
        users: () => api.DELETE('/api/admin/users/{user_id}', { params: { path: { user_id: id } } }),
        equipment: () => api.DELETE('/api/admin/equipment/{equipment_id}', { params: { path: { equipment_id: id } } }),
        bookings: () => api.DELETE('/api/admin/bookings/{booking_id}', { params: { path: { booking_id: id } } }),
        reviews: () => api.DELETE('/api/admin/reviews/{review_id}', { params: { path: { review_id: id } } }),
        categories: () => api.DELETE('/api/admin/categories/{category_id}', { params: { path: { category_id: id } } }),
      }[entity]
      const { error, response } = await call()
      if (!response.ok) throw new Error(getErrorMessage(error))
    },
    // Удаление в админке задевает всё: каталог, брони, отзывы, рейтинги
    onSuccess: () => qc.invalidateQueries(),
  })
}

export type TemplateItem = { name: string; example: string | null }

export function useSaveCategory() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async ({ id, name, specTemplate }: { id?: number; name: string; specTemplate: TemplateItem[] }) => {
      const body = { name, spec_template: specTemplate }
      const { data, error } = id
        ? await api.PUT('/api/admin/categories/{category_id}', { params: { path: { category_id: id } }, body })
        : await api.POST('/api/admin/categories', { body })
      if (!data) throw new Error(getErrorMessage(error))
      return data
    },
    onSuccess: () => qc.invalidateQueries(),
  })
}
