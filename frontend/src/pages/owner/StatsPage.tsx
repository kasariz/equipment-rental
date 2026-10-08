import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { ChevronLeft, ChevronRight } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router'
import { api, getErrorMessage } from '@/api/client'
import { PageSpinner } from '@/components/PageSpinner'
import { Button } from '@/components/ui/button'
import { formatRub, pluralize } from '@/lib/format'
import { cn } from '@/lib/utils'

const monthFmt = new Intl.DateTimeFormat('ru-RU', { month: 'long', year: 'numeric' })
const percent = (v: number) => `${Math.round(v * 100)}%`

function monthKey(d: Date) {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
}

function useOwnerStats(month: string) {
  return useQuery({
    queryKey: ['bookings', 'stats', month],
    queryFn: async () => {
      const { data, error } = await api.GET('/api/owner/stats', { params: { query: { month } } })
      if (!data) throw new Error(getErrorMessage(error))
      return data
    },
    placeholderData: keepPreviousData,
  })
}

function Kpi({ label, value, note }: { label: string; value: string; note?: string }) {
  return (
    <div className="rounded-xl border border-line bg-paper p-4">
      <p className="text-sm text-steel">{label}</p>
      <p className="font-display mt-1 text-2xl font-semibold">{value}</p>
      {note && <p className="mt-1 text-sm text-steel">{note}</p>}
    </div>
  )
}

export function StatsPage() {
  const [month, setMonth] = useState(() => {
    const d = new Date()
    return new Date(d.getFullYear(), d.getMonth(), 1)
  })
  const { data, isPending, isError, isFetching } = useOwnerStats(monthKey(month))
  const shift = (n: number) => setMonth(new Date(month.getFullYear(), month.getMonth() + n, 1))

  return (
    <div className="mx-auto max-w-5xl px-4 py-10 sm:px-6 sm:py-14">
      <Link to="/my/equipment" className="text-sm text-steel hover:text-ink">
        ← Моя техника
      </Link>
      <div className="mt-3 flex flex-wrap items-center justify-between gap-4">
        <h1 className="font-display text-3xl font-semibold tracking-tight">Статистика</h1>
        <div className="flex items-center gap-1">
          <Button variant="ghost" size="sm" aria-label="Предыдущий месяц" onClick={() => shift(-1)}>
            <ChevronLeft />
          </Button>
          <span className="min-w-36 text-center font-medium capitalize">{monthFmt.format(month)}</span>
          <Button variant="ghost" size="sm" aria-label="Следующий месяц" onClick={() => shift(1)}>
            <ChevronRight />
          </Button>
        </div>
      </div>

      {isPending && <PageSpinner />}
      {isError && <p className="mt-8 text-danger">Не удалось загрузить статистику.</p>}

      {data && (
        <div className={cn('mt-8 flex flex-col gap-10', isFetching && 'opacity-60')}>
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            <Kpi
              label="Заявок за месяц"
              value={String(data.requests.total)}
              note={data.requests.total ? `${percent(data.requests.confirmed / data.requests.total)} подтверждено` : undefined}
            />
            <Kpi label="Выручка, завершённые" value={formatRub(data.revenue_completed)} />
            <Kpi label="Ожидается" value={formatRub(data.revenue_expected)} note="подтверждённые и в работе" />
            <Kpi label="Средняя загрузка" value={percent(data.utilization)} note={`${data.equipment_count} ${pluralize(data.equipment_count, ['единица', 'единицы', 'единиц'])} техники`} />
          </div>

          <section>
            <h2 className="font-display text-xl font-semibold">Заявки по итогам</h2>
            <dl className="mt-4 grid grid-cols-2 gap-x-6 gap-y-2 sm:grid-cols-5">
              {(
                [
                  ['Подтверждены', data.requests.confirmed],
                  ['Ждут звонка', data.requests.pending],
                  ['Отклонены вами', data.requests.rejected],
                  ['Отменены клиентом', data.requests.cancelled],
                  ['Не подтверждены вовремя', data.requests.expired],
                ] as const
              ).map(([label, n]) => (
                <div key={label}>
                  <dt className="text-sm text-steel">{label}</dt>
                  <dd className="text-lg font-semibold">{n}</dd>
                </div>
              ))}
            </dl>
            {data.requests.expired > 0 && (
              <p className="mt-3 text-sm text-steel">
                Часть заявок сгорела без звонка. Подключите Telegram в профиле, чтобы узнавать о заявках сразу.
              </p>
            )}
          </section>

          <section>
            <h2 className="font-display text-xl font-semibold">Загрузка техники</h2>
            <p className="mt-1 text-sm text-steel">Занятые дни месяца: брони с сайта и дни, которые вы закрыли сами</p>
            {data.equipment.length === 0 ? (
              <p className="mt-4 text-steel">Техники пока нет.</p>
            ) : (
              <ul className="mt-4 divide-y divide-line rounded-xl border border-line bg-paper">
                {data.equipment.map((e) => (
                  <li key={e.id} className="grid gap-2 px-4 py-3 sm:grid-cols-[minmax(0,1fr)_minmax(0,2fr)_auto] sm:items-center sm:gap-4">
                    <Link to={`/my/equipment/${e.id}/calendar`} className="font-medium hover:underline">
                      {e.name}
                    </Link>
                    <div>
                      <div className="h-2.5 overflow-hidden rounded-full bg-concrete" role="img" aria-label={`Загрузка ${percent(e.utilization)}`}>
                        <div className="h-full rounded-full bg-signal" style={{ width: percent(e.utilization) }} />
                      </div>
                      <p className="mt-1 text-sm text-steel">
                        {e.busy_days} из {data.days_in_month} дн. ({percent(e.utilization)})
                        {e.blocked_days > 0 && `, из них ${e.blocked_days} закрыто вами`}
                      </p>
                    </div>
                    <p className="text-sm sm:text-right">
                      <span className="font-semibold">{formatRub(e.revenue)}</span>
                      <br />
                      <span className="text-steel">
                        {e.deals} {pluralize(e.deals, ['аренда', 'аренды', 'аренд'])}
                      </span>
                    </p>
                  </li>
                ))}
              </ul>
            )}
          </section>

          {data.equipment_count > 0 && (
            <section>
              <h2 className="font-display text-xl font-semibold">По дням</h2>
              <p className="mt-1 text-sm text-steel">Сколько единиц техники было занято каждый день</p>
              <div className="mt-4 overflow-x-auto">
                <div className="flex h-40 min-w-[560px] items-end gap-1 rounded-xl border border-line bg-paper p-3">
                  {data.days.map((d) => (
                    <div key={d.day} className="flex h-full flex-1 flex-col items-center justify-end gap-1" title={`${new Date(d.day).getDate()}: ${d.busy} из ${data.equipment_count}`}>
                      <div
                        className={cn('w-full rounded-sm', d.busy ? 'bg-ink' : 'bg-concrete')}
                        style={{ height: `${Math.max(4, (d.busy / data.equipment_count) * 100)}%` }}
                      />
                      <span className="text-[10px] text-steel">{new Date(d.day).getDate()}</span>
                    </div>
                  ))}
                </div>
              </div>
            </section>
          )}
        </div>
      )}
    </div>
  )
}
