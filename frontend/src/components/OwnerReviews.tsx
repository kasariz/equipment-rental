import { useOwnerReviews } from '@/features/reviews/api'
import { pluralize } from '@/lib/format'
import { Stars } from './Stars'

const dateFmt = new Intl.DateTimeFormat('ru-RU', { day: 'numeric', month: 'long', year: 'numeric' })

export function OwnerReviews({ ownerId, ownerName }: { ownerId: number; ownerName: string }) {
  const { data } = useOwnerReviews(ownerId)
  if (!data) return null

  return (
    <section>
      <h2 className="font-display text-xl font-semibold">Отзывы о владельце</h2>
      {data.count === 0 ? (
        <p className="mt-3 text-steel">У {ownerName} пока нет отзывов. Их оставляют арендаторы после завершения аренды.</p>
      ) : (
        <>
          <p className="mt-3 flex items-center gap-2">
            <Stars value={data.rating ?? 0} />
            <span className="font-semibold">{data.rating?.toLocaleString('ru-RU')}</span>
            <span className="text-steel">
              {data.count} {pluralize(data.count, ['отзыв', 'отзыва', 'отзывов'])}
            </span>
          </p>
          <ul className="mt-5 flex flex-col gap-4">
            {data.items.map((r) => (
              <li key={r.id} className="rounded-lg border border-line bg-paper p-4">
                <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
                  <Stars value={r.rating} />
                  <span className="font-medium">{r.author_name}</span>
                  <span className="text-sm text-steel">{dateFmt.format(new Date(r.created_at))}</span>
                </div>
                <p className="mt-1 text-sm text-steel">Аренда: {r.equipment_name}</p>
                {r.text && <p className="mt-2 break-words whitespace-pre-line">{r.text}</p>}
              </li>
            ))}
          </ul>
        </>
      )}
    </section>
  )
}
