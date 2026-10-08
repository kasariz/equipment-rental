/**
 * После выкладки новой версии файлы сборки получают новые имена, а старые удаляются.
 * Вкладка, открытая до обновления, при переходе на страницу просит старый файл и падает.
 * Лечение — один раз перезагрузить страницу: она подтянет свежую версию.
 * Метка в sessionStorage не даёт уйти в бесконечную перезагрузку, если файл не грузится по другой причине.
 */
const KEY = 'kovsh-reloaded-for-new-version'
const GUARD_MS = 10_000

export function reloadForNewVersion(): boolean {
  const last = Number(sessionStorage.getItem(KEY) ?? 0)
  if (Date.now() - last < GUARD_MS) return false
  sessionStorage.setItem(KEY, String(Date.now()))
  window.location.reload()
  return true
}

export function isChunkLoadError(error: unknown): boolean {
  const message = error instanceof Error ? error.message : String(error)
  return /Failed to fetch dynamically imported module|Importing a module script failed|error loading dynamically imported module/i.test(
    message,
  )
}
