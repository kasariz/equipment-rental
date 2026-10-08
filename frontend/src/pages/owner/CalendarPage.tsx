import { ChevronLeft, ChevronRight, Trash2 } from 'lucide-react'
import { useMemo, useState } from 'react'
import { Link, useParams } from 'react-router'
import { toast } from 'sonner'
import { PageSpinner } from '@/components/PageSpinner'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { useCalendar, useCreateBlock, useDeleteBlock } from '@/features/availability/api'
import { useEquipment } from '@/features/catalog/api'
import { useNow } from '@/hooks/useNow'
import { addDays, overlaps, sameDay, startOfDay, toLocalISO } from '@/lib/dates'
import { cn } from '@/lib/utils'
import { NotFoundPage } from '../NotFoundPage'

const monthFmt = new Intl.DateTimeFormat('ru-RU', { month: 'long', year: 'numeric' })
const dayFmt = new Intl.DateTimeFormat('ru-RU', { day: 'numeric', month: 'long' })
const WEEKDAYS = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']

/** Дни месяца в сетке с понедельника; пустые клетки до первого числа — null */
function monthGrid(month: Date): (Date | null)[] {
  const first = new Date(month.getFullYear(), month.getMonth(), 1)
  const days = new Date(month.getFullYear(), month.getMonth() + 1, 0).getDate()
  const lead = (first.getDay() + 6) % 7
  return [...Array<null>(lead).fill(null), ...Array.from({ length: days }, (_, i) => addDays(first, i))]
}

export function CalendarPage() {
  const id = Number(useParams().id)
  const { data: item, isPending } = useEquipment(id)
  const now = useNow()
  const today = startOfDay(new Date(now))
  const [month, setMonth] = useState(() => new Date(today.getFullYear(), today.getMonth(), 1))
  const [rangeStart, setRangeStart] = useState<Date | null>(null)
  const [rangeEnd, setRangeEnd] = useState<Date | null>(null)
  const [reason, setReason] = useState('')

  const from = toLocalISO(month)
  const to = toLocalISO(new Date(month.getFullYear(), month.getMonth() + 1, 1))
  const { data: events } = useCalendar(id, from, to)
  const createBlock = useCreateBlock(id)
  const deleteBlock = useDeleteBlock(id)

  const grid = useMemo(() => monthGrid(month), [month])
  const dayEvents = (d: Date) => (events ?? []).filter((e) => overlaps(d, addDays(d, 1), e.startDate, e.endDate))
  const [selFrom, selTo] =
    rangeStart && rangeEnd && rangeEnd < rangeStart ? [rangeEnd, rangeStart] : [rangeStart, rangeEnd ?? rangeStart]
  const inSelection = (d: Date) => selFrom && selTo && d >= selFrom && d <= selTo

  if (isPending) return <PageSpinner />
  if (!item) return <NotFoundPage />

  const pick = (d: Date) => {
    if (!rangeStart || rangeEnd) {
      setRangeStart(d)
      setRangeEnd(null)
    } else {
      setRangeEnd(d)
    }
  }

  const submit = () => {
    if (!selFrom || !selTo) return
    createBlock.mutate(
      { start: toLocalISO(selFrom), end: toLocalISO(addDays(selTo, 1)), reason: reason.trim() || null },
      {
        onSuccess: () => {
          toast.success('Дни закрыты для бронирования')
          setRangeStart(null)
          setRangeEnd(null)
          setReason('')
        },
        onError: (e) => toast.error(e.message),
      },
    )
  }

  const blocks = (events ?? []).filter((e) => e.kind === 'block')

  return (
    <div className="mx-auto max-w-3xl px-5 py-10 sm:px-6 sm:py-14">
      <Link to="/my/equipment" className="text-sm text-steel hover:text-ink">
        ← Моя техника
      </Link>
      <h1 className="font-display mt-3 text-3xl font-semibold tracking-tight">Календарь: {item.name}</h1>
      <p className="mt-2 max-w-prose text-steel">
        Закройте дни, когда техника занята на заказе не с сайта или на ремонте: клиенты не смогут их забронировать.
        Выберите первый и последний день.
      </p>

      <div className="mt-8 rounded-xl border border-line bg-paper p-4 sm:p-6">
        <div className="flex items-center justify-between">
          <Button variant="ghost" size="sm" aria-label="Предыдущий месяц" onClick={() => setMonth(new Date(month.getFullYear(), month.getMonth() - 1, 1))}>
            <ChevronLeft />
          </Button>
          <p className="font-display font-semibold capitalize">{monthFmt.format(month)}</p>
          <Button variant="ghost" size="sm" aria-label="Следующий месяц" onClick={() => setMonth(new Date(month.getFullYear(), month.getMonth() + 1, 1))}>
            <ChevronRight />
          </Button>
        </div>
        <div className="mt-4 grid grid-cols-7 gap-1 text-center text-xs text-steel">
          {WEEKDAYS.map((w) => (
            <span key={w}>{w}</span>
          ))}
        </div>
        <div className="mt-1 grid grid-cols-7 gap-1">
          {grid.map((d, i) => {
            if (!d) return <span key={`empty-${i}`} />
            const ev = dayEvents(d)
            const booked = ev.some((e) => e.kind === 'booking')
            const blocked = ev.some((e) => e.kind === 'block')
            const past = d < today
            const selected = inSelection(d)
            const title = ev.map((e) => (e.kind === 'block' ? `Закрыто${e.reason ? `: ${e.reason}` : ''}` : `Бронь: ${e.client_name}`)).join('\n')
            return (
              <button
                key={d.getTime()}
                type="button"
                disabled={past}
                title={title || undefined}
                aria-pressed={Boolean(selected)}
                aria-label={`${dayFmt.format(d)}${booked ? ', есть бронь' : ''}${blocked ? ', закрыто' : ''}`}
                onClick={() => pick(d)}
                className={cn(
                  'flex aspect-square flex-col items-center justify-center rounded-md border text-sm transition-colors',
                  past ? 'cursor-not-allowed border-transparent text-steel/40' : 'border-line hover:border-ink',
                  booked && !past && 'bg-signal/30',
                  blocked && !past && 'bg-[repeating-linear-gradient(135deg,var(--color-concrete)_0_6px,transparent_6px_12px)] text-steel',
                  selected && 'border-ink bg-ink text-paper',
                  sameDay(d, today) && !selected && 'font-semibold underline underline-offset-4',
                )}
              >
                {d.getDate()}
              </button>
            )
          })}
        </div>
        <div className="mt-4 flex flex-wrap gap-x-5 gap-y-1 text-sm text-steel">
          <span className="flex items-center gap-1.5">
            <span className="inline-block size-3 rounded-sm bg-signal/30" /> бронь клиента
          </span>
          <span className="flex items-center gap-1.5">
            <span className="inline-block size-3 rounded-sm bg-[repeating-linear-gradient(135deg,var(--color-line)_0_3px,transparent_3px_6px)]" /> закрыто вами
          </span>
        </div>
      </div>

      {selFrom && selTo && (
        <div className="mt-6 flex flex-col gap-3 rounded-xl border border-ink bg-paper p-4 sm:flex-row sm:items-end">
          <div className="flex-1">
            <p className="font-medium">
              {sameDay(selFrom, selTo) ? dayFmt.format(selFrom) : `${dayFmt.format(selFrom)} — ${dayFmt.format(selTo)}`}
            </p>
            <Input className="mt-2" value={reason} onChange={(e) => setReason(e.target.value)} maxLength={200} placeholder="Причина: заказ по телефону, ТО…" aria-label="Причина" />
          </div>
          <div className="flex gap-2">
            <Button onClick={submit} disabled={createBlock.isPending}>
              Закрыть дни
            </Button>
            <Button variant="ghost" onClick={() => { setRangeStart(null); setRangeEnd(null) }}>
              Отмена
            </Button>
          </div>
        </div>
      )}

      {blocks.length > 0 && (
        <section className="mt-8">
          <h2 className="font-display text-lg font-semibold">Закрытые дни в этом месяце</h2>
          <ul className="mt-3 divide-y divide-line rounded-xl border border-line bg-paper">
            {blocks.map((b) => (
              <li key={b.id} className="flex items-center justify-between gap-3 px-4 py-3">
                <span>
                  {dayFmt.format(b.startDate)} — {dayFmt.format(addDays(b.endDate, -1))}
                  {b.reason && <span className="text-steel">, {b.reason}</span>}
                </span>
                <Button variant="ghost" size="sm" onClick={() => deleteBlock.mutate(b.id, { onSuccess: () => toast.success('Дни снова открыты') })} aria-label="Открыть дни">
                  <Trash2 />
                  Открыть
                </Button>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  )
}
