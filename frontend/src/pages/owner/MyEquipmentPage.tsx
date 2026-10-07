import { Pencil, Plus, Trash2 } from 'lucide-react'
import { Link } from 'react-router'
import { toast } from 'sonner'
import { EquipmentImage } from '@/components/EquipmentImage'
import { PageSpinner } from '@/components/PageSpinner'
import { Button } from '@/components/ui/button'
import { ConfirmDialog } from '@/components/ui/confirm-dialog'
import { useDeleteEquipment, useMyEquipment } from '@/features/owner/api'
import { formatRub, statusLabels } from '@/lib/format'
import { cn } from '@/lib/utils'

const statusStyle = {
  available: 'bg-success/10 text-success',
  maintenance: 'bg-signal/25 text-ink',
  inactive: 'bg-ink/10 text-steel',
} as const

export function MyEquipmentPage() {
  const { data: items, isPending, isError } = useMyEquipment()
  const remove = useDeleteEquipment()

  return (
    <div className="mx-auto max-w-5xl px-4 py-10 sm:px-6 sm:py-14">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <h1 className="font-display text-3xl font-semibold tracking-tight">Моя техника</h1>
        <Button asChild>
          <Link to="/my/equipment/new">
            <Plus />
            Добавить технику
          </Link>
        </Button>
      </div>

      {isPending && <PageSpinner />}
      {isError && <p className="mt-8 text-danger">Не удалось загрузить список. Обновите страницу.</p>}

      {items && items.length === 0 && (
        <div className="mt-8 rounded-xl border border-dashed border-line p-8">
          <p className="font-medium">Вы ещё не добавили технику</p>
          <p className="mt-1 text-steel">
            Добавьте первую единицу: укажите цену, отметьте на карте, где она стоит, и загрузите фото.
          </p>
        </div>
      )}

      {items && items.length > 0 && (
        <ul className="mt-8 divide-y divide-line rounded-xl border border-line bg-paper">
          {items.map((item) => (
            <li key={item.id} className="grid grid-cols-[96px_minmax(0,1fr)] gap-4 p-4 sm:grid-cols-[120px_minmax(0,1fr)_auto] sm:items-center">
              <EquipmentImage src={item.cover_url} alt={item.name} className="aspect-[4/3] w-full rounded-md" />
              <div className="min-w-0">
                <Link to={`/equipment/${item.id}`} className="rounded-sm font-semibold hover:underline">
                  {item.name}
                </Link>
                <p className="text-sm text-steel">{item.category.name}</p>
                <div className="mt-2 flex flex-wrap items-center gap-2">
                  <span className={cn('rounded-full px-2.5 py-0.5 text-xs font-medium', statusStyle[item.status])}>
                    {statusLabels[item.status]}
                  </span>
                  <span className="text-sm">{formatRub(item.price_per_hour)} / час</span>
                </div>
              </div>
              <div className="col-span-2 flex gap-2 sm:col-span-1">
                <Button asChild variant="outline" size="sm">
                  <Link to={`/my/equipment/${item.id}/edit`}>
                    <Pencil />
                    Изменить
                  </Link>
                </Button>
                <ConfirmDialog
                  title={`Удалить «${item.name}»?`}
                  description="Объявление и все фото удалятся без возможности восстановления. Если технику нужно временно скрыть, смените статус на «Снята с размещения»."
                  confirmLabel="Удалить"
                  onConfirm={() =>
                    remove.mutate(item.id, {
                      onSuccess: () => toast.success('Техника удалена'),
                      onError: (e) => toast.error(e.message),
                    })
                  }
                  trigger={
                    <Button variant="ghost" size="sm" aria-label={`Удалить ${item.name}`}>
                      <Trash2 />
                    </Button>
                  }
                />
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
