import * as Dialog from '@radix-ui/react-dialog'
import { useState } from 'react'
import type { Booking } from '@/api/client'
import { useRenterReviews } from '@/features/reviews/api'
import { pluralize } from '@/lib/format'
import { Stars } from './Stars'

const dateFmt = new Intl.DateTimeFormat('ru-RU', { day: 'numeric', month: 'long', year: 'numeric' })

/** Рейтинг арендатора в карточке заявки: владелец видит его ещё до звонка */
export function RenterRating({ client }: { client: NonNullable<Booking['client']> }) {
  const [open, setOpen] = useState(false)
  const { data } = useRenterReviews(client.id ?? 0, open && client.id != null)

  if (!client.reviews_count || client.rating == null) {
    return <span className="text-sm text-steel">новый клиент, отзывов нет</span>
  }
  return (
    <Dialog.Root open={open} onOpenChange={setOpen}>
      <Dialog.Trigger asChild>
        <button type="button" className="inline-flex items-center gap-1 rounded-sm text-sm hover:underline">
          <Stars value={client.rating} className="[&_svg]:size-3.5" />
          {client.rating.toLocaleString('ru-RU')} · {client.reviews_count}{' '}
          {pluralize(client.reviews_count, ['отзыв', 'отзыва', 'отзывов'])}
        </button>
      </Dialog.Trigger>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-[2000] bg-ink/50" />
        <Dialog.Content className="fixed top-1/2 left-1/2 z-[2001] max-h-[80svh] w-[calc(100%-2rem)] max-w-lg -translate-x-1/2 -translate-y-1/2 overflow-y-auto rounded-xl bg-paper p-6 shadow-xl">
          <Dialog.Title className="font-display text-lg font-semibold">{client.full_name}</Dialog.Title>
          <Dialog.Description className="mt-1 text-steel">Отзывы владельцев техники об этом арендаторе</Dialog.Description>
          <ul className="mt-4 flex flex-col gap-3">
            {data?.items.map((r) => (
              <li key={r.id} className="rounded-lg border border-line p-3">
                <div className="flex flex-wrap items-center gap-x-2">
                  <Stars value={r.rating} />
                  <span className="text-sm text-steel">
                    {r.author_name}, {dateFmt.format(new Date(r.created_at))}
                  </span>
                </div>
                <p className="mt-1 text-sm text-steel">Аренда: {r.equipment_name}</p>
                {r.text && <p className="mt-1 break-words whitespace-pre-line">{r.text}</p>}
              </li>
            ))}
          </ul>
          <Dialog.Close className="mt-5 rounded-md border border-line px-4 py-2 text-sm hover:border-ink">Закрыть</Dialog.Close>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  )
}
