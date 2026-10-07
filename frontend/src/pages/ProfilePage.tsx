import { useNavigate } from 'react-router'
import { toast } from 'sonner'
import { TelegramConnect } from '@/components/TelegramConnect'
import { Button } from '@/components/ui/button'
import { roleLabels, useLogout, useMe } from '@/features/auth/api'

const dateFormat = new Intl.DateTimeFormat('ru-RU', { day: 'numeric', month: 'long', year: 'numeric' })

export function ProfilePage() {
  const { data: user } = useMe()
  const logout = useLogout()
  const navigate = useNavigate()
  if (!user) return null

  const rows = [
    ['Email', user.email],
    ['Телефон', user.phone ?? 'Не указан'],
    ['Роль', roleLabels[user.role]],
    ['С нами с', dateFormat.format(new Date(user.created_at))],
  ]

  return (
    <div className="mx-auto max-w-3xl px-4 py-10 sm:px-6 sm:py-14">
      <h1 className="font-display text-3xl font-semibold tracking-tight">{user.full_name}</h1>

      <dl className="mt-8 divide-y divide-line rounded-xl border border-line bg-paper">
        {rows.map(([term, value]) => (
          <div key={term} className="grid grid-cols-1 gap-1 px-5 py-4 sm:grid-cols-[180px_minmax(0,1fr)]">
            <dt className="text-sm text-steel">{term}</dt>
            <dd className="break-words">{value}</dd>
          </div>
        ))}
      </dl>

      <TelegramConnect isOwner={user.role === 'owner' || user.role === 'admin'} />

      <Button
        variant="outline"
        className="mt-8"
        disabled={logout.isPending}
        onClick={() =>
          logout.mutate(undefined, {
            onSuccess: () => {
              toast.success('Вы вышли из аккаунта')
              navigate('/')
            },
          })
        }
      >
        Выйти из аккаунта
      </Button>
    </div>
  )
}
