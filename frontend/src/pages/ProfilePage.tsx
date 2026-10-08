import { useNavigate } from 'react-router'
import { toast } from 'sonner'
import { Stars } from '@/components/Stars'
import { TelegramConnect } from '@/components/TelegramConnect'
import { useMyRatings } from '@/features/reviews/api'
import { Button } from '@/components/ui/button'
import { roleLabels, useLogout, useMe } from '@/features/auth/api'
import { formatPhone } from '@/lib/phone'

const dateFormat = new Intl.DateTimeFormat('ru-RU', { day: 'numeric', month: 'long', year: 'numeric' })

function MyRatings() {
  const { data } = useMyRatings()
  if (!data) return null
  const rows = [
    ['Как владелец', data.as_owner],
    ['Как арендатор', data.as_renter],
  ] as const
  return (
    <section className="mt-10">
      <h2 className="font-display text-lg font-semibold">Мой рейтинг</h2>
      <dl className="mt-3 grid gap-2">
        {rows.map(([label, r]) => (
          <div key={label} className="flex flex-wrap items-center gap-x-3">
            <dt className="w-36 text-steel">{label}</dt>
            <dd className="flex items-center gap-2">
              {r.rating != null ? (
                <>
                  <Stars value={r.rating} />
                  {r.rating.toLocaleString('ru-RU')}
                  <span className="text-sm text-steel">({r.count})</span>
                </>
              ) : (
                <span className="text-steel">отзывов пока нет</span>
              )}
            </dd>
          </div>
        ))}
      </dl>
    </section>
  )
}

export function ProfilePage() {
  const { data: user } = useMe()
  const logout = useLogout()
  const navigate = useNavigate()
  if (!user) return null

  const rows = [
    ['Email', user.email],
    ['Телефон', user.phone ? formatPhone(user.phone) : 'Не указан'],
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

      <MyRatings />

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
