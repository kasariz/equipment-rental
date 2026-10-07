import { CircleCheck, Phone } from 'lucide-react'
import { useMemo, useState } from 'react'
import { Link, useLocation } from 'react-router'
import type { Equipment, RateType } from '@/api/client'
import { Button } from '@/components/ui/button'
import { Field } from '@/components/ui/field'
import { Input } from '@/components/ui/input'
import { useMe } from '@/features/auth/api'
import { useNow } from '@/hooks/useNow'
import { useBusy, useCreateBooking, useQuote, type BookingParams } from '@/features/bookings/api'
import { addDays, addHours, atHour, formatPeriod, formatTime, overlaps, startOfDay, toLocalISO } from '@/lib/dates'
import { formatRub, pluralize } from '@/lib/format'
import { cn } from '@/lib/utils'

const LEAD_HOURS = 2 // как booking_min_lead_hours на бэкенде
const DAYS_SHOWN = 30
const FIRST_HOUR = 6
const LAST_HOUR = 20
const MAX_HOURS = 12
const PHONE_RE = /^\+?[\d\s()-]{10,20}$/

const weekdayFmt = new Intl.DateTimeFormat('ru-RU', { weekday: 'short' })
const monthFmt = new Intl.DateTimeFormat('ru-RU', { month: 'short' })

function durationHours(rate: RateType, quantity: number) {
  return rate === 'hourly' ? quantity : (quantity - 1) * 24 + 8
}

function Segmented({ value, onChange }: { value: RateType; onChange: (v: RateType) => void }) {
  const options: [RateType, string][] = [
    ['hourly', 'По часам'],
    ['shift', 'Посменно'],
  ]
  return (
    <div className="grid grid-cols-2 rounded-md bg-concrete p-1" role="radiogroup" aria-label="Тариф">
      {options.map(([v, label]) => (
        <button
          key={v}
          type="button"
          role="radio"
          aria-checked={value === v}
          onClick={() => onChange(v)}
          className={cn(
            'rounded px-3 py-2 text-sm font-medium transition-colors',
            value === v ? 'bg-paper shadow-sm' : 'text-steel hover:text-ink',
          )}
        >
          {label}
        </button>
      ))}
    </div>
  )
}

export function BookingForm({ item }: { item: Equipment }) {
  const { data: user } = useMe()
  const location = useLocation()
  const busyQuery = useBusy(item.id)
  const create = useCreateBooking()
  const now = useNow()

  const [rate, setRate] = useState<RateType>('hourly')
  const [hours, setHours] = useState(item.min_hours)
  const [shifts, setShifts] = useState(1)
  const [day, setDay] = useState<Date | null>(null)
  const [hour, setHour] = useState(8)
  const [withOperator, setWithOperator] = useState(false)
  const [phone, setPhone] = useState<string | null>(null) // null — ещё не трогали, берём из профиля
  const [address, setAddress] = useState('')
  const [comment, setComment] = useState('')
  const [phoneError, setPhoneError] = useState<string | null>(null)

  const quantity = rate === 'hourly' ? hours : shifts
  const duration = durationHours(rate, quantity)
  const busy = useMemo(() => busyQuery.data ?? [], [busyQuery.data])
  const phoneValue = phone ?? user?.phone ?? ''

  // Свободные часы начала для дня с учётом длительности и чужих броней
  const startsFor = useMemo(() => {
    const earliest = addHours(new Date(now), LEAD_HOURS)
    return (d: Date) =>
      Array.from({ length: LAST_HOUR - FIRST_HOUR + 1 }, (_, i) => {
        const h = FIRST_HOUR + i
        const start = atHour(d, h)
        const end = addHours(start, duration)
        const free = start >= earliest && !busy.some((b) => overlaps(start, end, b.start, b.end))
        return { hour: h, start, free }
      })
  }, [busy, duration, now])

  const days = useMemo(() => {
    const today = startOfDay(new Date(now))
    return Array.from({ length: DAYS_SHOWN }, (_, i) => {
      const d = addDays(today, i)
      return { date: d, hasStart: startsFor(d).some((s) => s.free) }
    })
  }, [startsFor, now])

  // Производное состояние вместо эффектов: если выбранное недоступно, берём ближайшее доступное
  const selectedDay = (day && days.find((d) => d.date.getTime() === day.getTime() && d.hasStart)) ?? days.find((d) => d.hasStart)
  const starts = selectedDay ? startsFor(selectedDay.date) : []
  const selectedStart = starts.find((s) => s.hour === hour && s.free) ?? starts.find((s) => s.free)

  const params: BookingParams | null = selectedStart
    ? {
        equipment_id: item.id,
        rate_type: rate,
        start: toLocalISO(selectedStart.start),
        quantity,
        with_operator: withOperator,
      }
    : null
  const quote = useQuote(params)

  const shiftPrice = item.price_per_shift ?? item.price_per_hour * 8
  const shiftIsCheaper = rate === 'hourly' && hours * item.price_per_hour > shiftPrice

  const submit = () => {
    if (!params) return
    if (!PHONE_RE.test(phoneValue.trim())) {
      setPhoneError('Введите номер в формате +7 900 123-45-67')
      return
    }
    setPhoneError(null)
    create.mutate({
      ...params,
      contact_phone: phoneValue.trim(),
      delivery_address: address.trim() || null,
      comment: comment.trim() || null,
    })
  }

  if (create.isSuccess) {
    const b = create.data
    return (
      <div className="flex flex-col gap-3" role="status">
        <CircleCheck className="size-8 text-success" aria-hidden />
        <p className="font-display text-lg font-semibold">Заявка отправлена</p>
        <p className="text-[15px]">
          {formatPeriod(b.start, b.end)}, {formatRub(b.total_price)}
        </p>
        <p className="text-[15px] text-steel">
          Владелец позвонит вам по номеру <span className="whitespace-nowrap text-ink">{b.contact_phone}</span>, чтобы
          подтвердить бронь. Если он не подтвердит её в течение суток, заявка отменится сама.
        </p>
        <div className="mt-2 flex flex-wrap gap-2">
          <Button asChild variant="dark">
            <Link to="/bookings">Мои брони</Link>
          </Button>
          <Button variant="ghost" onClick={() => create.reset()}>
            Новая заявка
          </Button>
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-5">
      <Segmented value={rate} onChange={setRate} />

      {/* Длительность */}
      <label className="flex flex-col gap-1.5 text-sm font-medium">
        {rate === 'hourly' ? 'Сколько часов' : 'Сколько смен'}
        <select
          className="h-11 rounded-md border border-line bg-paper px-3 text-[15px] hover:border-steel focus-visible:border-ink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-signal"
          value={quantity}
          onChange={(e) => (rate === 'hourly' ? setHours : setShifts)(Number(e.target.value))}
        >
          {rate === 'hourly'
            ? Array.from({ length: MAX_HOURS - item.min_hours + 1 }, (_, i) => item.min_hours + i).map((h) => (
                <option key={h} value={h}>
                  {h} {pluralize(h, ['час', 'часа', 'часов'])}
                </option>
              ))
            : Array.from({ length: 30 }, (_, i) => i + 1).map((n) => (
                <option key={n} value={n}>
                  {n} {pluralize(n, ['смена', 'смены', 'смен'])} ({n === 1 ? '8 часов' : `${n} ${pluralize(n, ['день', 'дня', 'дней'])} по 8 часов`})
                </option>
              ))}
        </select>
      </label>
      {shiftIsCheaper && (
        <p className="-mt-2 text-sm">
          Смена на 8 часов стоит {formatRub(shiftPrice)}, это выгоднее.{' '}
          <button
            type="button"
            className="font-medium underline underline-offset-4 hover:decoration-signal"
            onClick={() => {
              setRate('shift')
              setShifts(1)
            }}
          >
            Взять смену
          </button>
        </p>
      )}

      {/* День */}
      <fieldset>
        <legend className="mb-1.5 text-sm font-medium">День начала</legend>
        <div className="-mx-1 flex gap-1.5 overflow-x-auto px-1 pb-2">
          {days.map(({ date, hasStart }) => {
            const active = selectedDay?.date.getTime() === date.getTime()
            return (
              <button
                key={date.getTime()}
                type="button"
                disabled={!hasStart}
                aria-pressed={active}
                aria-label={`${date.toLocaleDateString('ru-RU', { weekday: 'long', day: 'numeric', month: 'long' })}${hasStart ? '' : ', занято'}`}
                onClick={() => setDay(date)}
                className={cn(
                  'flex w-14 shrink-0 flex-col items-center rounded-md border py-2 text-sm transition-colors',
                  active ? 'border-ink bg-ink text-paper' : 'border-line hover:border-ink',
                  !hasStart && 'cursor-not-allowed border-dashed text-steel/50 line-through hover:border-line',
                )}
              >
                <span className="text-xs capitalize opacity-80">{weekdayFmt.format(date)}</span>
                <span className="text-base font-semibold">{date.getDate()}</span>
                <span className="text-xs opacity-80">{monthFmt.format(date).replace('.', '')}</span>
              </button>
            )
          })}
        </div>
      </fieldset>

      {/* Время */}
      <label className="flex flex-col gap-1.5 text-sm font-medium">
        Время начала
        <select
          className="h-11 rounded-md border border-line bg-paper px-3 text-[15px] hover:border-steel focus-visible:border-ink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-signal"
          value={selectedStart?.hour ?? ''}
          onChange={(e) => setHour(Number(e.target.value))}
          disabled={!selectedStart}
        >
          {starts.map((s) => (
            <option key={s.hour} value={s.hour} disabled={!s.free}>
              {formatTime(s.start)}
              {!s.free ? ' — недоступно' : ''}
            </option>
          ))}
        </select>
      </label>
      {!selectedDay && !busyQuery.isPending && (
        <p className="text-sm text-danger">В ближайший месяц свободного времени под такую длительность нет.</p>
      )}

      {item.operator_available && item.operator_price_per_hour != null && (
        <label className="flex items-center gap-2.5 text-[15px]">
          <input
            type="checkbox"
            checked={withOperator}
            onChange={(e) => setWithOperator(e.target.checked)}
            className="size-4 accent-ink"
          />
          С оператором, +{formatRub(item.operator_price_per_hour)} в час
        </label>
      )}

      {/* Расчёт */}
      {quote.data && params && (
        <div className={cn('rounded-md bg-concrete p-4 text-[15px]', quote.isFetching && 'opacity-60')} aria-live="polite">
          <p className="font-medium">{formatPeriod(quote.data.start, quote.data.end)}</p>
          <dl className="mt-3 flex flex-col gap-1.5">
            <div className="flex justify-between gap-3">
              <dt className="text-steel">
                {rate === 'hourly'
                  ? `${hours} ч × ${formatRub(item.price_per_hour)}`
                  : `${shifts} ${pluralize(shifts, ['смена', 'смены', 'смен'])} × ${formatRub(shiftPrice)}`}
              </dt>
              <dd>{formatRub(quote.data.rental_price)}</dd>
            </div>
            {withOperator && (
              <div className="flex justify-between gap-3">
                <dt className="text-steel">Оператор, {quote.data.billable_hours} ч</dt>
                <dd>{formatRub(quote.data.operator_price)}</dd>
              </div>
            )}
            <div className="mt-1 flex justify-between gap-3 border-t border-line pt-2 text-lg font-semibold">
              <dt>Итого</dt>
              <dd>{formatRub(quote.data.total_price)}</dd>
            </div>
          </dl>
          {!quote.data.available && <p className="mt-2 text-sm text-danger">Это время только что заняли. Выберите другое.</p>}
        </div>
      )}
      {quote.error && <p className="text-sm text-danger">{quote.error.message}</p>}

      {!user ? (
        <Button asChild size="lg">
          <Link to="/login" state={{ from: location.pathname }}>
            Войти, чтобы забронировать
          </Link>
        </Button>
      ) : (
        <>
          <Field id="booking-phone" label="Телефон для подтверждения" error={phoneError ?? undefined} hint="Владелец позвонит, чтобы подтвердить бронь">
            <Input
              id="booking-phone"
              type="tel"
              autoComplete="tel"
              placeholder="+7 900 123-45-67"
              value={phoneValue}
              onChange={(e) => setPhone(e.target.value)}
              aria-invalid={Boolean(phoneError)}
              aria-describedby={phoneError ? 'booking-phone-error' : 'booking-phone-hint'}
            />
          </Field>
          <Field id="booking-address" label="Адрес объекта (необязательно)" hint="Если нужна доставка. Её стоимость обсудите по телефону">
            <Input id="booking-address" value={address} onChange={(e) => setAddress(e.target.value)} maxLength={500} />
          </Field>
          <Field id="booking-comment" label="Комментарий (необязательно)">
            <textarea
              id="booking-comment"
              value={comment}
              onChange={(e) => setComment(e.target.value)}
              maxLength={1000}
              placeholder="Что нужно сделать: траншея под фундамент, погрузка грунта…"
              className="min-h-20 w-full rounded-md border border-line bg-paper px-3.5 py-2.5 text-[15px] hover:border-steel focus-visible:border-ink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-signal"
            />
          </Field>

          {create.isError && (
            <p role="alert" className="rounded-md border border-danger/30 bg-danger/5 px-3 py-2 text-sm text-danger">
              {create.error.message}
            </p>
          )}

          <Button size="lg" onClick={submit} disabled={!params || create.isPending || quote.data?.available === false}>
            <Phone />
            {create.isPending ? 'Отправляем…' : 'Отправить заявку'}
          </Button>
          <p className="-mt-2 text-center text-sm text-steel">Бронь подтверждается после звонка владельца</p>
        </>
      )}
    </div>
  )
}
