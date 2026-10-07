import { Phone } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router'
import { toast } from 'sonner'
import type { Booking, BookingStatus } from '@/api/client'
import { RejectDialog } from '@/components/booking/RejectDialog'
import { PageSpinner } from '@/components/PageSpinner'
import { Button } from '@/components/ui/button'
import { useOwnerAction, useOwnerBookings, useRejectBooking } from '@/features/bookings/api'
import { formatPeriod } from '@/lib/dates'
import { bookingStatusForOwner, bookingStatusStyle, describeRate, formatRub, telHref } from '@/lib/format'
import { cn } from '@/lib/utils'

const TABS: { key: string; label: string; statuses: BookingStatus[]; empty: string }[] = [
  { key: 'new', label: 'Новые', statuses: ['pending'], empty: 'Новых заявок нет. Они появятся здесь автоматически.' },
  { key: 'upcoming', label: 'Подтверждённые', statuses: ['confirmed'], empty: 'Подтверждённых броней пока нет.' },
  { key: 'active', label: 'В работе', statuses: ['active'], empty: 'Сейчас ни одна техника не в аренде.' },
  {
    key: 'archive',
    label: 'Архив',
    statuses: ['completed', 'cancelled', 'rejected', 'expired'],
    empty: 'Здесь будут завершённые и отменённые брони.',
  },
]

const createdFmt = new Intl.DateTimeFormat('ru-RU', { day: 'numeric', month: 'long', hour: '2-digit', minute: '2-digit' })

function RequestCard({ b }: { b: Booking }) {
  const action = useOwnerAction()
  const reject = useRejectBooking()
  const busy = action.isPending || reject.isPending
  const run = (kind: 'confirm' | 'start' | 'complete', done: string) =>
    action.mutate({ id: b.id, action: kind }, { onSuccess: () => toast.success(done), onError: (e) => toast.error(e.message) })
  const doReject = (reason: string) =>
    reject.mutate({ id: b.id, reason }, { onSuccess: () => toast.success('Заявка отклонена'), onError: (e) => toast.error(e.message) })
  const showPhone = b.status === 'pending' || b.status === 'confirmed' || b.status === 'active'

  return (
    <li className="grid gap-4 rounded-xl border border-line bg-paper p-4 sm:p-5 md:grid-cols-[1fr_auto]">
      <div className="flex min-w-0 flex-col gap-2">
        <span className={cn('self-start rounded-full px-2.5 py-0.5 text-xs font-medium', bookingStatusStyle[b.status])}>
          {bookingStatusForOwner[b.status]}
        </span>
        <Link to={`/equipment/${b.equipment.id}`} className="self-start rounded-sm font-semibold hover:underline">
          {b.equipment.name}
        </Link>
        <p className="text-[15px]">
          {formatPeriod(b.start, b.end)}
          <span className="text-steel">, {describeRate(b.rate_type, b.quantity)}{b.with_operator ? ', с оператором' : ', без оператора'}</span>
        </p>
        <p className="font-semibold">{formatRub(b.total_price)}</p>

        <dl className="mt-1 grid gap-x-4 gap-y-1 text-sm sm:grid-cols-[auto_1fr]">
          <dt className="text-steel">Клиент</dt>
          <dd>{b.client?.full_name}</dd>
          {b.delivery_address && (
            <>
              <dt className="text-steel">Адрес объекта</dt>
              <dd>{b.delivery_address}</dd>
            </>
          )}
          {b.comment && (
            <>
              <dt className="text-steel">Комментарий</dt>
              <dd className="whitespace-pre-line">{b.comment}</dd>
            </>
          )}
          {b.reject_reason && (
            <>
              <dt className="text-steel">Причина отказа</dt>
              <dd>{b.reject_reason}</dd>
            </>
          )}
          <dt className="text-steel">Заявка от</dt>
          <dd>{createdFmt.format(new Date(b.created_at))}</dd>
        </dl>
      </div>

      <div className="flex flex-col gap-2 md:w-56">
        {showPhone && (
          <Button asChild variant={b.status === 'pending' ? 'primary' : 'outline'}>
            <a href={telHref(b.contact_phone)}>
              <Phone />
              {b.contact_phone}
            </a>
          </Button>
        )}
        {b.status === 'pending' && (
          <>
            <Button variant="dark" disabled={busy} onClick={() => run('confirm', 'Бронь подтверждена')}>
              Подтвердить
            </Button>
            <RejectDialog
              title="Отклонить заявку?"
              confirmLabel="Отклонить"
              onConfirm={doReject}
              trigger={<Button variant="ghost" disabled={busy}>Отклонить</Button>}
            />
          </>
        )}
        {b.status === 'confirmed' && (
          <>
            <Button variant="dark" disabled={busy} onClick={() => run('start', 'Аренда началась')}>
              Начать аренду
            </Button>
            <RejectDialog
              title="Отменить подтверждённую бронь?"
              confirmLabel="Отменить бронь"
              onConfirm={doReject}
              trigger={<Button variant="ghost" disabled={busy}>Отменить бронь</Button>}
            />
          </>
        )}
        {b.status === 'active' && (
          <Button variant="dark" disabled={busy} onClick={() => run('complete', 'Аренда завершена')}>
            Завершить аренду
          </Button>
        )}
      </div>
    </li>
  )
}

export function RequestsPage() {
  const { data, isPending, isError } = useOwnerBookings()
  const [tab, setTab] = useState('new')
  const current = TABS.find((t) => t.key === tab)!
  const count = (statuses: BookingStatus[]) => data?.filter((b) => statuses.includes(b.status)).length ?? 0
  const items = (data ?? []).filter((b) => current.statuses.includes(b.status))
  if (tab === 'archive') items.reverse() // в архиве сначала свежие

  return (
    <div className="mx-auto max-w-4xl px-4 py-10 sm:px-6 sm:py-14">
      <h1 className="font-display text-3xl font-semibold tracking-tight">Заявки</h1>
      <p className="mt-2 max-w-prose text-steel">
        Позвоните клиенту, договоритесь о деталях и подтвердите бронь. Неподтверждённая заявка отменится через сутки.
      </p>

      <div className="-mx-4 mt-8 flex gap-1 overflow-x-auto border-b border-line px-4" role="tablist">
        {TABS.map((t) => {
          const n = count(t.statuses)
          return (
            <button
              key={t.key}
              type="button"
              role="tab"
              aria-selected={tab === t.key}
              onClick={() => setTab(t.key)}
              className={cn(
                '-mb-px flex shrink-0 items-center gap-2 border-b-[3px] px-3 py-2.5 text-[15px] transition-colors',
                tab === t.key ? 'border-signal font-medium text-ink' : 'border-transparent text-steel hover:text-ink',
              )}
            >
              {t.label}
              {n > 0 && t.key !== 'archive' && (
                <span className={cn('rounded-full px-2 text-xs leading-5', t.key === 'new' ? 'bg-signal text-ink' : 'bg-ink/10')}>{n}</span>
              )}
            </button>
          )
        })}
      </div>

      {isPending && <PageSpinner />}
      {isError && <p className="mt-8 text-danger">Не удалось загрузить заявки. Обновите страницу.</p>}
      {data && items.length === 0 && <p className="mt-8 text-steel">{current.empty}</p>}
      {items.length > 0 && (
        <ul className="mt-6 flex flex-col gap-3" role="tabpanel">
          {items.map((b) => (
            <RequestCard key={b.id} b={b} />
          ))}
        </ul>
      )}
    </div>
  )
}
