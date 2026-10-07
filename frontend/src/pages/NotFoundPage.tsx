import { Link } from 'react-router'
import { Button } from '@/components/ui/button'

export function NotFoundPage() {
  return (
    <div className="mx-auto max-w-6xl px-4 py-24 sm:px-6">
      <p className="font-display text-7xl font-bold text-ink/15">404</p>
      <h1 className="font-display mt-4 text-3xl font-semibold">Такой страницы нет</h1>
      <p className="mt-3 text-steel">Возможно, ссылка устарела или в адресе опечатка.</p>
      <Button asChild className="mt-8">
        <Link to="/">На главную</Link>
      </Button>
    </div>
  )
}
