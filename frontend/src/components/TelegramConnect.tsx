import { BellRing, Send } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { useCreateTelegramLink, useTelegramStatus, useUnlinkTelegram } from '@/features/telegram/api'

/** Подключение уведомлений: ссылка на бота → человек жмёт Start → сайт видит привязку */
export function TelegramConnect({ isOwner }: { isOwner: boolean }) {
  const [linkUrl, setLinkUrl] = useState<string | null>(null)
  const { data: status } = useTelegramStatus({ waitingForLink: linkUrl !== null })
  const createLink = useCreateTelegramLink()
  const unlink = useUnlinkTelegram()
  const qc = useQueryClient()

  const connected = status?.connected ?? false
  useEffect(() => {
    if (linkUrl && connected) {
      toast.success('Telegram подключён')
      qc.invalidateQueries({ queryKey: ['auth', 'me'] })
    }
  }, [linkUrl, connected, qc])

  if (!status?.enabled) return null // бот не настроен на сервере — блок не показываем

  const what = isOwner
    ? 'Бот пришлёт новую заявку сразу, с телефоном клиента, и сообщит, если клиент отменит бронь.'
    : 'Бот сообщит, когда владелец подтвердит или отклонит вашу заявку.'

  return (
    <section className="mt-10 rounded-xl border border-line bg-paper p-5 sm:p-6">
      <h2 className="font-display flex items-center gap-2 text-lg font-semibold">
        <BellRing className="size-5" aria-hidden />
        Уведомления в Telegram
      </h2>
      <p className="mt-2 max-w-prose text-steel">{what}</p>

      {connected ? (
        <div className="mt-5 flex flex-wrap items-center gap-3">
          <span className="rounded-full bg-success/10 px-3 py-1 text-sm font-medium text-success">Подключено</span>
          <Button
            variant="ghost"
            size="sm"
            disabled={unlink.isPending}
            onClick={() =>
              unlink.mutate(undefined, {
                onSuccess: () => {
                  setLinkUrl(null)
                  toast.success('Уведомления в Telegram отключены')
                },
                onError: (e) => toast.error(e.message),
              })
            }
          >
            Отключить
          </Button>
        </div>
      ) : linkUrl ? (
        <div className="mt-5 flex flex-col gap-3">
          <Button asChild className="self-start">
            <a href={linkUrl} target="_blank" rel="noreferrer">
              <Send />
              Открыть бота в Telegram
            </a>
          </Button>
          <p className="text-sm text-steel" aria-live="polite">
            В боте нажмите «Запустить» (Start). Эта страница обновится сама. Ссылка действует 10 минут.
          </p>
        </div>
      ) : (
        <Button
          className="mt-5"
          variant="dark"
          disabled={createLink.isPending}
          onClick={() =>
            createLink.mutate(undefined, { onSuccess: setLinkUrl, onError: (e) => toast.error(e.message) })
          }
        >
          <Send />
          {createLink.isPending ? 'Готовим ссылку…' : 'Подключить Telegram'}
        </Button>
      )}
    </section>
  )
}
