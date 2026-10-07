import { Suspense, type ReactNode } from 'react'
import { createBrowserRouter } from 'react-router'
import { Layout } from '@/components/Layout'
import { PageSpinner } from '@/components/PageSpinner'
import { RequireAuth } from '@/features/auth/RequireAuth'
import { HomePage } from '@/pages/HomePage'
import {
  CatalogPage,
  EquipmentCreatePage,
  EquipmentEditPage,
  EquipmentPage,
  MyBookingsPage,
  MyEquipmentPage,
  RequestsPage,
} from '@/pages/lazy'
import { LoginPage } from '@/pages/LoginPage'
import { NotFoundPage } from '@/pages/NotFoundPage'
import { ProfilePage } from '@/pages/ProfilePage'
import { RegisterPage } from '@/pages/RegisterPage'

const page = (node: ReactNode) => <Suspense fallback={<PageSpinner />}>{node}</Suspense>
const ownerOnly = (node: ReactNode) => page(<RequireAuth roles={['owner', 'admin']}>{node}</RequireAuth>)

export const router = createBrowserRouter([
  {
    element: <Layout />,
    children: [
      { index: true, element: <HomePage /> },
      { path: 'catalog', element: page(<CatalogPage />) },
      { path: 'equipment/:id', element: page(<EquipmentPage />) },
      { path: 'login', element: <LoginPage /> },
      { path: 'register', element: <RegisterPage /> },
      { path: 'profile', element: <RequireAuth><ProfilePage /></RequireAuth> },
      { path: 'bookings', element: page(<RequireAuth><MyBookingsPage /></RequireAuth>) },
      { path: 'my/requests', element: ownerOnly(<RequestsPage />) },
      { path: 'my/equipment', element: ownerOnly(<MyEquipmentPage />) },
      { path: 'my/equipment/new', element: ownerOnly(<EquipmentCreatePage />) },
      { path: 'my/equipment/:id/edit', element: ownerOnly(<EquipmentEditPage />) },
      { path: '*', element: <NotFoundPage /> },
    ],
  },
])
