import type { ReactNode } from 'react'
import { Navigate, useLocation } from 'react-router'
import type { UserRole } from '@/api/client'
import { PageSpinner } from '@/components/PageSpinner'
import { useMe } from './api'

/**
 * Пускает на страницу только вошедших (и, если указано, с нужной ролью).
 * Остальных отправляет на вход и потом возвращает обратно.
 * Это удобство для интерфейса, а не защита: права всё равно проверяет бэкенд.
 */
export function RequireAuth({ children, roles }: { children: ReactNode; roles?: UserRole[] }) {
  const { data: user, isPending } = useMe()
  const location = useLocation()

  if (isPending) return <PageSpinner />
  if (!user) return <Navigate to="/login" replace state={{ from: location.pathname }} />
  if (roles && !roles.includes(user.role)) {
    return (
      <div className="mx-auto max-w-6xl px-4 py-24 sm:px-6">
        <h1 className="font-display text-3xl font-semibold">
          {roles.includes('owner') ? 'Раздел для владельцев техники' : 'Раздел для администраторов'}
        </h1>
        <p className="mt-3 max-w-prose text-steel">
          {roles.includes('owner')
            ? 'Чтобы сдавать технику, нужен аккаунт владельца. Зарегистрируйте его на другой email.'
            : 'У вашего аккаунта нет доступа к этому разделу.'}
        </p>
      </div>
    )
  }
  return children
}
