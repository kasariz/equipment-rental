import createClient from 'openapi-fetch'
import type { components, paths } from './schema'

// Типизированный клиент: пути, тела запросов и ответы берутся из OpenAPI-схемы бэкенда.
// После изменений в API: npm run gen:api
export const api = createClient<paths>({ baseUrl: '' })

export type User = components['schemas']['UserRead']
export type UserRole = User['role']
export type Category = components['schemas']['CategoryRead']
export type EquipmentListItem = components['schemas']['EquipmentListItem']
export type Equipment = components['schemas']['EquipmentRead']
export type EquipmentStatus = Equipment['status']
export type Photo = components['schemas']['PhotoRead']
export type Booking = components['schemas']['BookingRead']
export type BookingStatus = Booking['status']
export type RateType = Booking['rate_type']
export type Quote = components['schemas']['QuoteRead']
export type BusyInterval = components['schemas']['BusyInterval']

/** Достаёт понятное сообщение из ответа FastAPI: {detail: "..."} или ошибки валидации 422. */
export function getErrorMessage(error: unknown, fallback = 'Что-то пошло не так. Попробуйте ещё раз.'): string {
  if (error && typeof error === 'object' && 'detail' in error) {
    const { detail } = error as { detail: unknown }
    if (typeof detail === 'string') return detail
    if (Array.isArray(detail) && detail[0]?.msg) return String(detail[0].msg)
  }
  return fallback
}
