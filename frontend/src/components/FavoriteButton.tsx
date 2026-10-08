import { Heart } from 'lucide-react'
import { useNavigate } from 'react-router'
import { toast } from 'sonner'
import { useMe } from '@/features/auth/api'
import { useToggleFavorite } from '@/features/favorites/api'
import { cn } from '@/lib/utils'

export function FavoriteButton({ id, active, className }: { id: number; active: boolean; className?: string }) {
  const { data: user } = useMe()
  const toggle = useToggleFavorite()
  const navigate = useNavigate()
  const label = active ? 'Убрать из избранного' : 'Добавить в избранное'

  return (
    <button
      type="button"
      aria-label={label}
      aria-pressed={active}
      title={label}
      disabled={toggle.isPending}
      onClick={() => {
        if (!user) {
          navigate('/login', { state: { from: window.location.pathname } })
          return
        }
        toggle.mutate({ id, favorite: !active }, { onError: (e) => toast.error(e.message) })
      }}
      className={cn(
        'flex size-9 items-center justify-center rounded-full bg-paper/90 shadow-sm transition-colors hover:bg-paper',
        className,
      )}
    >
      <Heart className={cn('size-5', active ? 'fill-danger text-danger' : 'text-steel')} aria-hidden />
    </button>
  )
}
