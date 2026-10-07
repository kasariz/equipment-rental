import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api, getErrorMessage } from '@/api/client'

const statusKey = ['telegram', 'status'] as const

/** Настроен ли бот на сервере и привязан ли Telegram к аккаунту */
export function useTelegramStatus(options?: { enabled?: boolean; waitingForLink?: boolean }) {
  return useQuery({
    queryKey: statusKey,
    queryFn: async () => {
      const { data, error } = await api.GET('/api/telegram/status')
      if (!data) throw new Error(getErrorMessage(error))
      return data
    },
    enabled: options?.enabled ?? true,
    // Пока человек нажимает Start в боте, проверяем раз в 3 секунды, не привязался ли чат
    refetchInterval: options?.waitingForLink ? 3000 : false,
  })
}

export function useCreateTelegramLink() {
  return useMutation({
    mutationFn: async () => {
      const { data, error } = await api.POST('/api/telegram/link')
      if (!data) throw new Error(getErrorMessage(error))
      return data.url
    },
  })
}

export function useUnlinkTelegram() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async () => {
      const { error, response } = await api.DELETE('/api/telegram/link')
      if (!response.ok) throw new Error(getErrorMessage(error))
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: statusKey })
      qc.invalidateQueries({ queryKey: ['auth', 'me'] })
    },
  })
}
