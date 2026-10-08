/**
 * Установка сайта как приложения (PWA).
 * Service worker регистрируем только в собранной версии: в разработке он мешал бы
 * горячей перезагрузке Vite. Событие установки браузер присылает один раз —
 * запоминаем его, чтобы показать свою кнопку «Установить приложение».
 */

type InstallPrompt = Event & { prompt: () => Promise<void>; userChoice: Promise<{ outcome: string }> }

let deferred: InstallPrompt | null = null
const listeners = new Set<() => void>()

export function setupPwa() {
  if (import.meta.env.PROD && 'serviceWorker' in navigator) {
    window.addEventListener('load', () => {
      navigator.serviceWorker.register('/sw.js').catch(() => {
        /* без service worker сайт просто работает как обычный */
      })
    })
  }
  window.addEventListener('beforeinstallprompt', (e) => {
    e.preventDefault()
    deferred = e as InstallPrompt
    listeners.forEach((fn) => fn())
  })
  window.addEventListener('appinstalled', () => {
    deferred = null
    listeners.forEach((fn) => fn())
  })
}

export function canInstall(): boolean {
  return deferred !== null
}

export async function install(): Promise<boolean> {
  if (!deferred) return false
  await deferred.prompt()
  const { outcome } = await deferred.userChoice
  deferred = null
  listeners.forEach((fn) => fn())
  return outcome === 'accepted'
}

export function onInstallChange(fn: () => void): () => void {
  listeners.add(fn)
  return () => listeners.delete(fn)
}

export function isStandalone(): boolean {
  return window.matchMedia('(display-mode: standalone)').matches
}

export function isIos(): boolean {
  return /iphone|ipad|ipod/i.test(navigator.userAgent)
}
