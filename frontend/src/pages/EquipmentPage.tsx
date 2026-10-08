import { ArrowLeft, MapPin, Pencil } from 'lucide-react'
import { useState } from 'react'
import { Link, useParams } from 'react-router'
import type { Equipment } from '@/api/client'
import { BookingForm } from '@/components/booking/BookingForm'
import { EquipmentImage } from '@/components/EquipmentImage'
import { PointMap } from '@/components/map/PointMap'
import { EquipmentCard } from '@/components/EquipmentCard'
import { FavoriteButton } from '@/components/FavoriteButton'
import { OwnerReviews } from '@/components/OwnerReviews'
import { useSimilar } from '@/features/favorites/api'
import { PageSpinner } from '@/components/PageSpinner'
import { Stars } from '@/components/Stars'
import { Button } from '@/components/ui/button'
import { HorizontalScroller } from '@/components/ui/horizontal-scroller'
import { useMe } from '@/features/auth/api'
import { useEquipment } from '@/features/catalog/api'
import { formatRub, statusLabels } from '@/lib/format'
import { cn } from '@/lib/utils'
import { NotFoundPage } from './NotFoundPage'

function Gallery({ item }: { item: Equipment }) {
  const [index, setIndex] = useState(0)
  const photos = item.photos
  const current = photos[index]

  return (
    <div>
      <EquipmentImage src={current?.url} alt={item.name} className="aspect-[4/3] w-full rounded-xl" />
      {photos.length > 1 && (
        <div className="mt-3">
          <HorizontalScroller className="gap-2" fadeFrom="from-concrete" label="Фото">
          {photos.map((p, i) => (
            <button
              key={p.id}
              type="button"
              onClick={() => setIndex(i)}
              aria-label={`Фото ${i + 1} из ${photos.length}`}
              aria-current={i === index}
              className={cn(
                'w-24 shrink-0 overflow-hidden rounded-md border-2 transition-colors',
                i === index ? 'border-ink' : 'border-transparent opacity-70 hover:opacity-100',
              )}
            >
              <img src={p.url} alt="" className="aspect-[4/3] w-full object-cover" />
            </button>
          ))}
          </HorizontalScroller>
        </div>
      )}
    </div>
  )
}

function PricePanel({ item, isOwner }: { item: Equipment; isOwner: boolean }) {
  const rows: [string, string][] = [
    ['Минимальный заказ', `${item.min_hours} ч`],
    ['Оператор', 'Включён в цену'],
  ]
  if (item.price_per_shift != null) rows.unshift(['Смена, 8 часов', formatRub(item.price_per_shift)])

  return (
    <div className="rounded-xl border border-line bg-paper p-6">
      <p className="text-3xl font-semibold">
        {formatRub(item.price_per_hour)}
        <span className="text-base font-normal text-steel"> / час</span>
      </p>
      <dl className="mt-5 divide-y divide-line border-y border-line">
        {rows.map(([term, value]) => (
          <div key={term} className="flex justify-between gap-4 py-2.5 text-[15px]">
            <dt className="text-steel">{term}</dt>
            <dd className="text-right font-medium">{value}</dd>
          </div>
        ))}
      </dl>

      {isOwner ? (
        <Button asChild variant="dark" size="lg" className="mt-6 w-full">
          <Link to={`/my/equipment/${item.id}/edit`}>
            <Pencil />
            Редактировать
          </Link>
        </Button>
      ) : item.status === 'available' ? (
        <div className="mt-6 border-t border-line pt-6">
          <h2 className="font-display mb-4 text-lg font-semibold">Забронировать</h2>
          <BookingForm item={item} />
        </div>
      ) : null}

      <p className="mt-6 flex flex-wrap items-center gap-x-2 text-sm text-steel">
        Владелец: <span className="text-ink">{item.owner.full_name}</span>
        {item.owner.rating != null && (
          <a href="#reviews" className="inline-flex items-center gap-1 rounded-sm text-ink hover:underline">
            <Stars value={item.owner.rating} className="[&_svg]:size-3.5" />
            {item.owner.rating.toLocaleString('ru-RU')} ({item.owner.reviews_count})
          </a>
        )}
      </p>
    </div>
  )
}

function SimilarEquipment({ id }: { id: number }) {
  const { data } = useSimilar(id)
  if (!data?.length) return null
  return (
    <section>
      <h2 className="font-display text-xl font-semibold">Похожая техника рядом</h2>
      <ul className="mt-4 grid grid-cols-1 gap-2">
        {data.slice(0, 4).map((s) => (
          <li key={s.id}>
            <EquipmentCard item={s} />
          </li>
        ))}
      </ul>
    </section>
  )
}

export function EquipmentPage() {
  const id = Number(useParams().id)
  const { data: item, isPending, isError } = useEquipment(id)
  const { data: user } = useMe()

  if (isPending) return <PageSpinner />
  if (isError) {
    return <p className="mx-auto max-w-6xl px-5 py-14 text-danger sm:px-6">Не удалось загрузить технику. Обновите страницу.</p>
  }
  if (!item) return <NotFoundPage />

  const isOwner = user != null && (user.id === item.owner.id || user.role === 'admin')

  return (
    <div className="mx-auto max-w-6xl px-5 py-6 sm:px-6 sm:py-10">
      <Link
        to={`/catalog?category=${item.category.slug}`}
        className="inline-flex items-center gap-1.5 rounded-sm text-sm text-steel hover:text-ink"
      >
        <ArrowLeft className="size-4" aria-hidden />
        {item.category.name}
      </Link>

      {item.status !== 'available' && (
        <p className="mt-4 rounded-md border border-signal-dark/40 bg-signal/15 px-4 py-3 text-sm">
          Статус: {statusLabels[item.status].toLowerCase()}. Арендаторы эту технику сейчас не видят.
        </p>
      )}

      <div className="mt-3 flex items-start justify-between gap-4">
        <h1 className="font-display text-3xl leading-tight font-semibold tracking-tight sm:text-4xl">{item.name}</h1>
        <FavoriteButton id={item.id} active={item.is_favorite} className="mt-1 shrink-0 border border-line" />
      </div>
      {item.address && (
        <p className="mt-2 flex items-center gap-1.5 text-steel">
          <MapPin className="size-4 shrink-0" aria-hidden />
          {item.address}
        </p>
      )}

      <div className="mt-8 grid grid-cols-1 gap-8 lg:grid-cols-[minmax(0,1fr)_360px] lg:items-start">
        <div className="flex flex-col gap-10">
          <Gallery item={item} />

          {item.specs.length > 0 && (
            <section>
              <h2 className="font-display text-xl font-semibold">Характеристики</h2>
              <dl className="mt-4 divide-y divide-line border-y border-line">
                {item.specs.map((s) => (
                  <div key={s.name} className="grid grid-cols-2 gap-4 py-3">
                    <dt className="text-steel">{s.name}</dt>
                    <dd className="font-medium">{s.value}</dd>
                  </div>
                ))}
              </dl>
            </section>
          )}

          {item.description && (
            <section>
              <h2 className="font-display text-xl font-semibold">Описание</h2>
              <p className="mt-4 max-w-prose whitespace-pre-line">{item.description}</p>
            </section>
          )}

          <SimilarEquipment id={item.id} />

          <div id="reviews" className="scroll-mt-6">
            <OwnerReviews ownerId={item.owner.id} ownerName={item.owner.full_name} />
          </div>

          <section>
            <h2 className="font-display text-xl font-semibold">Где стоит техника</h2>
            <div className="mt-4 h-72 overflow-hidden rounded-xl border border-line">
              <PointMap lat={item.latitude} lng={item.longitude} label="Здесь" />
            </div>
          </section>
        </div>

        <aside className="lg:sticky lg:top-6">
          <PricePanel item={item} isOwner={isOwner} />
        </aside>
      </div>
    </div>
  )
}
