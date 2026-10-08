import { Phone, Star } from 'lucide-react'
import { Link } from 'react-router'
import { toast } from 'sonner'
import type { Booking } from '@/api/client'
import { EquipmentImage } from '@/components/EquipmentImage'
import { ReviewDialog } from '@/components/ReviewDialog'
import { PageSpinner } from '@/components/PageSpinner'
import { Button } from '@/components/ui/button'
import { ConfirmDialog } from '@/components/ui/confirm-dialog'
import { useCancelBooking, useMyBookings } from '@/features/bookings/api'
import { useNow } from '@/hooks/useNow'
import { formatPeriod } from '@/lib/dates'
import { bookingStatusForClient, bookingStatusStyle, describeRate, formatRub, telHref } from '@/lib/format'
import { formatPhone } from '@/lib/phone'
import { cn } from '@/lib/utils'

const CURRENT = ['pending', 'confirmed', 'active'] as const

function BookingCard({ b, now }: { b: Booking; now: number }) {
  const cancel = useCancelBooking()
  const canCancel = (b.status === 'pending' || b.status === 'confirmed') && new Date(b.start).getTime() > now

  return (
    <li className="grid grid-cols-1 gap-4 rounded-xl border border-line bg-paper p-4 sm:grid-cols-[140px_minmax(0,1fr)] sm:p-5">
      <EquipmentImage src={b.equipment.cover_url} alt={b.equipment.name} className="aspect-[4/3] w-full rounded-md max-sm:hidden" />
      <div className="flex min-w-0 flex-col gap-2">
        <span className={cn('self-start rounded-full px-2.5 py-0.5 text-xs font-medium', bookingStatusStyle[b.status])}>
          {bookingStatusForClient[b.status]}
        </span>
        <Link to={`/equipment/${b.equipment.id}`} className="self-start rounded-sm font-semibold hover:underline">
          {b.equipment.name}
        </Link>
        <p className="text-[15px]">
          {formatPeriod(b.start, b.end)}
          <span className="text-steel">, {describeRate(b.rate_type, b.quantity)}</span>
        </p>
        <p className="font-semibold">{formatRub(b.total_price)}</p>

        {b.status === 'pending' && (
          <p className="text-sm text-steel">Владелец позвонит по номеру {formatPhone(b.contact_phone)}, чтобы подтвердить бронь.</p>
        )}
        {b.status === 'rejected' && b.reject_reason && <p className="text-sm text-steel">Причина: {b.reject_reason}</p>}
        {b.owner && (
          <p className="flex flex-wrap items-center gap-x-2 text-sm">
            <span className="text-steel">Владелец: {b.owner.full_name}</span>
            {b.owner.phone && (
              <a href={telHref(b.owner.phone)} className="inline-flex items-center gap-1 font-medium underline underline-offset-4 hover:decoration-signal">
                <Phone className="size-3.5" aria-hidden />
                {formatPhone(b.owner.phone)}
              </a>
            )}
          </p>
        )}

        {/* Владельца можно оценить после аренды или если он отклонил заявку / отменил бронь */}
        {(b.status === 'completed' || b.status === 'rejected') &&
          (b.reviewed ? (
            <p className="text-sm text-steel">Вы оставили отзыв. Спасибо!</p>
          ) : (
            <ReviewDialog
              bookingId={b.id}
              subjectName={b.owner?.full_name ?? 'владельца'}
              target="owner"
              trigger={
                <Button variant="outline" size="sm" className="mt-1 self-start">
                  <Star />
                  Оценить владельца
                </Button>
              }
            />
          ))}

        {canCancel && (
          <ConfirmDialog
            title="Отменить бронь?"
            description="Время освободится, и технику смогут забронировать другие."
            confirmLabel="Отменить бронь"
            onConfirm={() =>
              cancel.mutate(b.id, {
                onSuccess: () => toast.success('Бронь отменена'),
                onError: (e) => toast.error(e.message),
              })
            }
            trigger={
              <Button variant="outline" size="sm" className="mt-1 self-start" disabled={cancel.isPending}>
                Отменить
              </Button>
            }
          />
        )}
      </div>
    </li>
  )
}

export function MyBookingsPage() {
  const { data, isPending, isError } = useMyBookings()
  const now = useNow()
  const current = data?.filter((b) => (CURRENT as readonly string[]).includes(b.status)) ?? []
  const history = data?.filter((b) => !(CURRENT as readonly string[]).includes(b.status)) ?? []

  return (
    <div className="mx-auto max-w-3xl px-4 py-10 sm:px-6 sm:py-14">
      <h1 className="font-display text-3xl font-semibold tracking-tight">Мои брони</h1>
      {isPending && <PageSpinner />}
      {isError && <p className="mt-8 text-danger">Не удалось загрузить брони. Обновите страницу.</p>}

      {data && data.length === 0 && (
        <div className="mt-8 rounded-xl border border-dashed border-line p-8">
          <p className="font-medium">Броней пока нет</p>
          <p className="mt-1 text-steel">Найдите технику в каталоге и отправьте заявку, владелец перезвонит.</p>
          <Button asChild className="mt-5">
            <Link to="/catalog">Открыть каталог</Link>
          </Button>
        </div>
      )}

      {current.length > 0 && (
        <ul className="mt-8 flex flex-col gap-3">
          {current.map((b) => (
            <BookingCard key={b.id} b={b} now={now} />
          ))}
        </ul>
      )}
      {history.length > 0 && (
        <section className="mt-12">
          <h2 className="font-display text-xl font-semibold">История</h2>
          <ul className="mt-4 flex flex-col gap-3">
            {history.map((b) => (
              <BookingCard key={b.id} b={b} now={now} />
            ))}
          </ul>
        </section>
      )}
    </div>
  )
}
