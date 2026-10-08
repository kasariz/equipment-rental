import { RotateCw } from 'lucide-react'
import { Link, useRouteError } from 'react-router'
import { Button } from '@/components/ui/button'
import { isChunkLoadError } from '@/lib/newVersion'

/** Вместо технического «Unexpected Application Error!» — понятная страница с выходом */
export function ErrorPage() {
  const error = useRouteError()
  const updated = isChunkLoadError(error)

  return (
    <div className="mx-auto max-w-2xl px-4 py-24 sm:px-6">
      <h1 className="font-display text-3xl font-semibold">{updated ? 'Сайт обновился' : 'Что-то пошло не так'}</h1>
      <p className="mt-3 text-steel">
        {updated
          ? 'Пока страница была открыта, мы выпустили новую версию. Обновите страницу, чтобы продолжить.'
          : 'Попробуйте обновить страницу. Если ошибка повторяется, напишите администратору.'}
      </p>
      <div className="mt-8 flex flex-wrap gap-3">
        <Button onClick={() => window.location.reload()}>
          <RotateCw />
          Обновить
        </Button>
        <Button asChild variant="outline">
          <a href="/">На главную</a>
        </Button>
      </div>
      {!updated && import.meta.env.DEV && (
        <pre className="mt-8 overflow-x-auto rounded-md bg-ink p-4 text-xs text-paper">{String(error)}</pre>
      )}
      <Link to="/" className="sr-only">
        На главную
      </Link>
    </div>
  )
}
