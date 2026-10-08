import { Link } from 'react-router'
import { EquipmentCard } from '@/components/EquipmentCard'
import { PageSpinner } from '@/components/PageSpinner'
import { Button } from '@/components/ui/button'
import { useFavorites } from '@/features/favorites/api'

export function FavoritesPage() {
  const { data, isPending } = useFavorites()
  return (
    <div className="mx-auto max-w-3xl px-4 py-10 sm:px-6 sm:py-14">
      <h1 className="font-display text-3xl font-semibold tracking-tight">Избранное</h1>
      {isPending && <PageSpinner />}
      {data && data.length === 0 && (
        <div className="mt-8 rounded-xl border border-dashed border-line p-8">
          <p className="font-medium">Здесь пока пусто</p>
          <p className="mt-1 text-steel">Нажмите на сердечко в карточке техники, чтобы сохранить её сюда.</p>
          <Button asChild className="mt-5">
            <Link to="/catalog">Открыть каталог</Link>
          </Button>
        </div>
      )}
      <ul className="mt-8 flex flex-col gap-2">
        {data?.map((item) => (
          <li key={item.id}>
            {item.status !== 'available' && (
              <p className="mb-1 text-sm text-steel">Сейчас не сдаётся</p>
            )}
            <EquipmentCard item={item} />
          </li>
        ))}
      </ul>
    </div>
  )
}
