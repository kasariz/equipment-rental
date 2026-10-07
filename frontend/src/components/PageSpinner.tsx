import { LoaderCircle } from 'lucide-react'

export function PageSpinner() {
  return (
    <div className="flex min-h-[40vh] items-center justify-center" role="status">
      <LoaderCircle className="size-6 animate-spin text-steel" aria-hidden />
      <span className="sr-only">Загрузка</span>
    </div>
  )
}
