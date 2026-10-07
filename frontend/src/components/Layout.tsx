import { LogOut, UserRound } from 'lucide-react'
import { Link, NavLink, Outlet, useLocation, useNavigate } from 'react-router'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { useLogout, useMe } from '@/features/auth/api'
import { useOwnerBookings } from '@/features/bookings/api'
import { cn } from '@/lib/utils'
import { Logo } from './Logo'

const navLinkClass = ({ isActive }: { isActive: boolean }) =>
  cn(
    'shrink-0 whitespace-nowrap rounded-sm px-1 py-1 text-[15px] transition-colors hover:text-ink',
    isActive ? 'text-ink font-medium underline decoration-signal decoration-[3px] underline-offset-8' : 'text-steel',
  )

function UserArea() {
  const { data: user, isPending } = useMe()
  const logout = useLogout()
  const navigate = useNavigate()

  if (isPending) return <div className="h-9 w-40" aria-hidden />

  if (!user) {
    return (
      <div className="flex items-center gap-2">
        <Button asChild variant="ghost" size="sm">
          <Link to="/login">Войти</Link>
        </Button>
        <Button asChild variant="dark" size="sm">
          <Link to="/register">Регистрация</Link>
        </Button>
      </div>
    )
  }

  return (
    <div className="flex items-center gap-1">
      <Button asChild variant="ghost" size="sm">
        <Link to="/profile">
          <UserRound />
          <span className="max-w-40 truncate">{user.full_name}</span>
        </Link>
      </Button>
      <Button
        variant="ghost"
        size="sm"
        aria-label="Выйти"
        title="Выйти"
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
        <LogOut />
      </Button>
    </div>
  )
}

function NavLinks({ className }: { className?: string }) {
  const { data: user } = useMe()
  const isOwner = user?.role === 'owner' || user?.role === 'admin'
  // Счётчик новых заявок обновляется сам раз в 30 секунд
  const { data: pending } = useOwnerBookings(['pending'], { enabled: isOwner })
  const newCount = pending?.length ?? 0

  return (
    <nav className={className} aria-label="Основная навигация">
      <NavLink to="/catalog" className={navLinkClass}>
        Каталог
      </NavLink>
      {user && (
        <NavLink to="/bookings" className={navLinkClass}>
          Мои брони
        </NavLink>
      )}
      {isOwner && (
        <>
          <NavLink to="/my/requests" className={navLinkClass}>
            <span className="inline-flex items-center gap-1.5">
              Заявки
              {newCount > 0 && (
                <span className="rounded-full bg-signal px-1.5 text-xs leading-5 font-semibold text-ink" aria-label={`новых: ${newCount}`}>
                  {newCount}
                </span>
              )}
            </span>
          </NavLink>
          <NavLink to="/my/equipment" className={navLinkClass}>
            Моя техника
          </NavLink>
        </>
      )}
    </nav>
  )
}

export function Layout() {
  // В каталоге карта занимает весь экран, футер под ней не нужен
  const hideFooter = useLocation().pathname === '/catalog'
  return (
    <div className="flex min-h-svh flex-col">
      <div className="hazard-stripe h-1.5" aria-hidden />
      <header className="border-b border-line bg-paper">
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between gap-6 px-4 sm:px-6">
          <div className="flex items-center gap-8">
            <Logo />
            <NavLinks className="hidden items-center gap-6 md:flex" />
          </div>
          <UserArea />
        </div>
        {/* На телефоне навигация — отдельной прокручиваемой строкой под шапкой */}
        <NavLinks className="flex gap-5 overflow-x-auto border-t border-line px-4 py-2 [scrollbar-width:none] md:hidden" />
      </header>

      <main className="flex-1">
        <Outlet />
      </main>

      <footer className={cn('border-t border-line', hideFooter && 'hidden')}>
        <div className="mx-auto max-w-6xl px-4 py-6 text-sm text-steel sm:px-6">
          Ковш — аренда спецтехники у владельцев рядом с вашим объектом
        </div>
      </footer>
    </div>
  )
}
