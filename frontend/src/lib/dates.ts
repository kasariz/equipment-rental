/** Работа с датами в часовом поясе пользователя */

export function startOfDay(d: Date): Date {
  const x = new Date(d)
  x.setHours(0, 0, 0, 0)
  return x
}

export function addDays(d: Date, days: number): Date {
  const x = new Date(d)
  x.setDate(x.getDate() + days)
  return x
}

export function addHours(d: Date, hours: number): Date {
  return new Date(d.getTime() + hours * 3_600_000)
}

export function atHour(day: Date, hour: number): Date {
  const x = startOfDay(day)
  x.setHours(hour)
  return x
}

export function sameDay(a: Date, b: Date): boolean {
  return a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate()
}

/** ISO-строка с локальным смещением: 2026-10-10T09:00:00+03:00. Сервер видит именно 09:00 */
export function toLocalISO(d: Date): string {
  const pad = (n: number) => String(Math.abs(n)).padStart(2, '0')
  const offset = -d.getTimezoneOffset()
  const sign = offset >= 0 ? '+' : '-'
  return (
    `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}` +
    `T${pad(d.getHours())}:00:00${sign}${pad(Math.trunc(offset / 60))}:${pad(offset % 60)}`
  )
}

export function overlaps(aStart: Date, aEnd: Date, bStart: Date, bEnd: Date): boolean {
  return aStart < bEnd && bStart < aEnd
}

const dayFmt = new Intl.DateTimeFormat('ru-RU', { weekday: 'short', day: 'numeric', month: 'short' })
const timeFmt = new Intl.DateTimeFormat('ru-RU', { hour: '2-digit', minute: '2-digit' })
const dateTimeFmt = new Intl.DateTimeFormat('ru-RU', { day: 'numeric', month: 'long', hour: '2-digit', minute: '2-digit' })

/** «пт, 10 окт., 09:00–14:00» или «10 октября, 09:00 — 12 октября, 17:00» */
export function formatPeriod(start: Date | string, end: Date | string): string {
  const s = new Date(start)
  const e = new Date(end)
  if (sameDay(s, e)) return `${dayFmt.format(s)}, ${timeFmt.format(s)}–${timeFmt.format(e)}`
  return `${dateTimeFmt.format(s)} — ${dateTimeFmt.format(e)}`
}

export function formatTime(d: Date): string {
  return timeFmt.format(d)
}
