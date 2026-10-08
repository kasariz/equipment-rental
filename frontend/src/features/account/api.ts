import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api, getErrorMessage } from '@/api/client'

export function useSiteInfo() {
  return useQuery({
    queryKey: ['site-info'],
    queryFn: async () => {
      const { data } = await api.GET('/api/site-info')
      return data ?? { operator_name: '', operator_email: '', password_reset_by_email: false }
    },
    staleTime: Infinity,
  })
}

export function useRequestPasswordReset() {
  return useMutation({
    mutationFn: async (email: string) => {
      const { data, error } = await api.POST('/api/auth/password-reset/request', { body: { email } })
      if (!data) throw new Error(getErrorMessage(error))
      return data
    },
  })
}

export function useConfirmPasswordReset() {
  return useMutation({
    mutationFn: async ({ token, password }: { token: string; password: string }) => {
      const { error, response } = await api.POST('/api/auth/password-reset/confirm', { body: { token, password } })
      if (!response.ok) throw new Error(getErrorMessage(error))
    },
  })
}

export function useDeleteAccount() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (password: string) => {
      const { error, response } = await api.DELETE('/api/auth/me', { body: { password } })
      if (!response.ok) throw new Error(getErrorMessage(error))
    },
    onSuccess: () => qc.clear(),
  })
}
