import { useState } from 'react'
import { useNavigate } from 'react-router'
import { toast } from 'sonner'
import { InstallApp } from '@/components/InstallApp'
import { Stars } from '@/components/Stars'
import { TelegramConnect } from '@/components/TelegramConnect'
import { useMyRatings } from '@/features/reviews/api'
import type { UserRole } from '@/api/client'
import { Button } from '@/components/ui/button'
import { PasswordInput } from '@/components/ui/password-input'
import { useDeleteAccount } from '@/features/account/api'
import { roleLabels, useLogout, useMe } from '@/features/auth/api'
import { formatPhone } from '@/lib/phone'

const dateFormat = new Intl.DateTimeFormat('ru-RU', { day: 'numeric', month: 'long', year: 'numeric' })

function MyRatings({ role }: { role: UserRole }) {
  const { data } = useMyRatings()
  if (!data) return null
  // Рейтинг владельца — только владельцам. Рейтинг арендатора — арендаторам, а владельцу,
  // только если он сам что-то арендовал и получил отзывы
  const rows = [
    ...(role === 'owner' ? [['Как владелец', data.as_owner] as const] : []),
    ...(role === 'client' || data.as_renter.count > 0 ? [['Как арендатор', data.as_renter] as const] : []),
  ]
  if (rows.length === 0) return null
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

function DeleteAccount({ isOwner }: { isOwner: boolean }) {
  const [password, setPassword] = useState('')
  const [open, setOpen] = useState(false)
  const del = useDeleteAccount()
  const navigate = useNavigate()

  return (
    <section className="mt-12 border-t border-line pt-8">
      <h2 className="font-display text-lg font-semibold">Удаление аккаунта</h2>
      <p className="mt-2 max-w-prose text-sm text-steel">
        Вместе с аккаунтом удалятся {isOwner ? 'ваша техника, брони и отзывы' : 'ваши брони, избранное и отзывы'}.
        Восстановить данные будет нельзя.
      </p>
      {!open ? (
        <Button variant="outline" className="mt-4 border-danger/40 text-danger hover:border-danger" onClick={() => setOpen(true)}>
          Удалить аккаунт
        </Button>
      ) : (
        <form
          className="mt-4 flex max-w-sm flex-col gap-3"
          onSubmit={(e) => {
            e.preventDefault()
            del.mutate(password, {
              onSuccess: () => {
                toast.success('Аккаунт удалён')
                navigate('/', { replace: true })
              },
              onError: (err) => toast.error(err.message),
            })
          }}
        >
          <label className="flex flex-col gap-1.5 text-sm font-medium">
            Для подтверждения введите пароль
            <PasswordInput autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} />
          </label>
          <div className="flex gap-2">
            <Button type="submit" className="bg-danger text-paper hover:bg-danger/90" disabled={!password || del.isPending}>
              Удалить навсегда
            </Button>
            <Button type="button" variant="ghost" onClick={() => setOpen(false)}>
              Отмена
            </Button>
          </div>
        </form>
      )}
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
    <div className="mx-auto max-w-3xl px-5 py-10 sm:px-6 sm:py-14">
      <h1 className="font-display text-3xl font-semibold tracking-tight">{user.full_name}</h1>

      <dl className="mt-8 divide-y divide-line rounded-xl border border-line bg-paper">
        {rows.map(([term, value]) => (
          <div key={term} className="grid grid-cols-1 gap-1 px-5 py-4 sm:grid-cols-[180px_minmax(0,1fr)]">
            <dt className="text-sm text-steel">{term}</dt>
            <dd className="break-words">{value}</dd>
          </div>
        ))}
      </dl>

      <MyRatings role={user.role} />

      <InstallApp />

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

      <DeleteAccount isOwner={user.role !== 'client'} />
    </div>
  )
}
