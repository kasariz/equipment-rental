import { lazy } from 'react'

// Страницы с картой и формами грузятся отдельными кусками: Яндекс Карты не нужны на главной и при входе
export const CatalogPage = lazy(() => import('@/pages/CatalogPage').then((m) => ({ default: m.CatalogPage })))
export const EquipmentPage = lazy(() => import('@/pages/EquipmentPage').then((m) => ({ default: m.EquipmentPage })))
export const MyEquipmentPage = lazy(() =>
  import('@/pages/owner/MyEquipmentPage').then((m) => ({ default: m.MyEquipmentPage })),
)
export const EquipmentCreatePage = lazy(() =>
  import('@/pages/owner/EquipmentFormPage').then((m) => ({ default: m.EquipmentCreatePage })),
)
export const EquipmentEditPage = lazy(() =>
  import('@/pages/owner/EquipmentFormPage').then((m) => ({ default: m.EquipmentEditPage })),
)
export const MyBookingsPage = lazy(() => import('@/pages/MyBookingsPage').then((m) => ({ default: m.MyBookingsPage })))
export const RequestsPage = lazy(() =>
  import('@/pages/owner/RequestsPage').then((m) => ({ default: m.RequestsPage })),
)
export const AdminPage = lazy(() => import('@/pages/admin/AdminPage').then((m) => ({ default: m.AdminPage })))
export const FavoritesPage = lazy(() => import('@/pages/FavoritesPage').then((m) => ({ default: m.FavoritesPage })))
export const CalendarPage = lazy(() => import('@/pages/owner/CalendarPage').then((m) => ({ default: m.CalendarPage })))
