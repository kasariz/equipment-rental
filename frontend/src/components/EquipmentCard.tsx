import type { Ref } from 'react'
import { Link } from 'react-router'
import type { EquipmentListItem } from '@/api/client'
import { formatDistance, formatRub } from '@/lib/format'
import { cn } from '@/lib/utils'
import { EquipmentImage } from './EquipmentImage'

type Props = {
  item: EquipmentListItem
  active?: boolean
  onHover?: (id: number | null) => void
  ref?: Ref<HTMLAnchorElement>
}

export function EquipmentCard({ item, active, onHover, ref }: Props) {
  return (
    <Link
      ref={ref}
      to={`/equipment/${item.id}`}
      onMouseEnter={() => onHover?.(item.id)}
      onMouseLeave={() => onHover?.(null)}
      onFocus={() => onHover?.(item.id)}
      className={cn(
        'grid grid-cols-[112px_1fr] gap-4 rounded-lg border bg-paper p-3 transition-colors sm:grid-cols-[136px_1fr]',
        active ? 'border-ink' : 'border-transparent hover:border-line',
      )}
    >
      <EquipmentImage src={item.cover_url} alt={item.name} className="aspect-[4/3] w-full rounded-md" />
      <div className="flex min-w-0 flex-col">
        <p className="text-sm text-steel">{item.category.name}</p>
        <h3 className="mt-0.5 leading-snug font-semibold">{item.name}</h3>
        <p className="mt-1 truncate text-sm text-steel">{item.address ?? 'Адрес не указан'}</p>
        <div className="mt-auto flex flex-wrap items-baseline gap-x-3 pt-2">
          <span className="text-lg font-semibold">
            {formatRub(item.price_per_hour)}
            <span className="text-sm font-normal text-steel"> / час</span>
          </span>
          {item.distance_km != null && (
            <span className="text-sm text-steel">{formatDistance(item.distance_km)} от вас</span>
          )}
          {item.operator_available && <span className="text-sm text-steel">есть оператор</span>}
        </div>
      </div>
    </Link>
  )
}
