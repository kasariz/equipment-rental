const rub = new Intl.NumberFormat('ru-RU', { maximumFractionDigits: 0 })

/** 2500 → «2 500 ₽» */
export function formatRub(value: number): string {
  return `${rub.format(value)} ₽`
}

export function formatDistance(km: number): string {
  return km < 1 ? `${Math.round(km * 1000)} м` : `${km.toLocaleString('ru-RU', { maximumFractionDigits: 1 })} км`
}

export function pluralize(n: number, forms: [string, string, string]): string {
  const mod10 = n % 10
  const mod100 = n % 100
  if (mod10 === 1 && mod100 !== 11) return forms[0]
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14)) return forms[1]
  return forms[2]
}

export const statusLabels = {
  available: 'Сдаётся',
  maintenance: 'На ремонте',
  inactive: 'Снята с размещения',
} as const

/** Подписи статусов брони: клиенту и владельцу важно разное */
export const bookingStatusForClient = {
  pending: 'Ждёт звонка владельца',
  confirmed: 'Подтверждена',
  active: 'Техника в работе',
  completed: 'Завершена',
  cancelled: 'Вы отменили',
  rejected: 'Отклонена владельцем',
  expired: 'Не подтверждена вовремя',
} as const

export const bookingStatusForOwner = {
  pending: 'Новая, нужно позвонить',
  confirmed: 'Подтверждена',
  active: 'В работе',
  completed: 'Завершена',
  cancelled: 'Отменена клиентом',
  rejected: 'Отклонена',
  expired: 'Не подтверждена вовремя',
} as const

export const bookingStatusStyle = {
  pending: 'bg-signal/30 text-ink',
  confirmed: 'bg-success/10 text-success',
  active: 'bg-ink text-paper',
  completed: 'bg-ink/10 text-steel',
  cancelled: 'bg-ink/10 text-steel',
  rejected: 'bg-danger/10 text-danger',
  expired: 'bg-ink/10 text-steel',
} as const

export function describeRate(rateType: 'hourly' | 'shift', quantity: number): string {
  return rateType === 'hourly'
    ? `${quantity} ${pluralize(quantity, ['час', 'часа', 'часов'])}`
    : `${quantity} ${pluralize(quantity, ['смена', 'смены', 'смен'])} по 8 ч`
}

/** Кликабельная ссылка для звонка: убираем пробелы, скобки и дефисы */
export function telHref(phone: string): string {
  return `tel:${phone.replace(/[^\d+]/g, '')}`
}
