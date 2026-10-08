import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { RouterProvider } from 'react-router'
import { Toaster } from 'sonner'
import { router } from './router'
import './index.css'
import { reloadForNewVersion } from './lib/newVersion'
import { setupPwa } from './lib/pwa'

const queryClient = new QueryClient({
  defaultOptions: { queries: { refetchOnWindowFocus: false } },
})

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
      <Toaster position="top-center" richColors />
    </QueryClientProvider>
  </StrictMode>,
)

setupPwa()

// Старая вкладка после выкладки новой версии: один раз перезагружаемся вместо ошибки
window.addEventListener('vite:preloadError', (event) => {
  if (reloadForNewVersion()) event.preventDefault()
})
