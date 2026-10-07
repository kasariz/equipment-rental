import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api, getErrorMessage, type User } from '@/api/client'
import type { components } from '@/api/schema'

type LoginBody = components['schemas']['UserLogin']
type RegisterBody = components['schemas']['UserCreate']

export const meQueryKey = ['auth', 'me'] as const

/** Текущий пользователь или null, если не вошёл. Токен лежит в httpOnly-cookie, фронт его не видит. */
export function useMe() {
  return useQuery({
    queryKey: meQueryKey,
    queryFn: async (): Promise<User | null> => {
      const { data, response } = await api.GET('/api/auth/me')
      if (response.status === 401) return null
      if (!data) throw new Error('Не удалось загрузить профиль')
      return data
    },
    staleTime: 5 * 60 * 1000,
    retry: false,
  })
}

export function useLogin() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (body: LoginBody) => {
      const { data, error } = await api.POST('/api/auth/login', { body })
      if (!data) throw new Error(getErrorMessage(error))
      return data
    },
    onSuccess: (user) => qc.setQueryData(meQueryKey, user),
  })
}

export function useRegister() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (body: RegisterBody) => {
      const { data, error } = await api.POST('/api/auth/register', { body })
      if (!data) throw new Error(getErrorMessage(error))
      return data
    },
    onSuccess: (user) => qc.setQueryData(meQueryKey, user),
  })
}

export function useLogout() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async () => {
      await api.POST('/api/auth/logout')
    },
    onSuccess: () => {
      qc.setQueryData(meQueryKey, null)
      // Сбрасываем все личные данные из кэша прошлого пользователя
      qc.removeQueries({ predicate: (q) => q.queryKey[0] !== 'auth' })
    },
  })
}

export const roleLabels: Record<User['role'], string> = {
  client: 'Арендатор',
  owner: 'Владелец техники',
  admin: 'Администратор',
}
