import { LoaderCircle, Minus, Plus } from 'lucide-react'
import type { ReactNode, RefObject } from 'react'
import type { YMap } from '@yandex/ymaps3-types'
import { useYMaps, type YMapsComponents } from '@/lib/ymaps'

/** Показывает загрузку или понятную ошибку, а когда API готов — саму карту */
export function MapFrame({ children }: { children: (ymaps: YMapsComponents) => ReactNode }) {
  const { ymaps, error } = useYMaps()
  if (error) {
    return (
      <div className="flex size-full items-center justify-center bg-concrete p-6 text-center text-sm text-steel" role="alert">
        {error.message}
      </div>
    )
  }
  if (!ymaps) {
    return (
      <div className="flex size-full items-center justify-center bg-concrete" role="status">
        <LoaderCircle className="size-6 animate-spin text-steel" aria-hidden />
        <span className="sr-only">Загружаем карту</span>
      </div>
    )
  }
  return <>{children(ymaps)}</>
}

/** Кнопки масштаба поверх карты: колесо мыши работает и так, но кнопки нужны тем, у кого его нет */
export function ZoomButtons({ mapRef }: { mapRef: RefObject<YMap | null> }) {
  const zoom = (delta: number) => {
    const map = mapRef.current
    if (map) map.setLocation({ zoom: map.zoom + delta, duration: 200 })
  }
  const btn =
    'flex size-10 items-center justify-center bg-paper text-ink transition-colors hover:bg-concrete focus-visible:z-10'
  return (
    <div className="absolute top-3 right-3 z-10 flex flex-col overflow-hidden rounded-md border border-line shadow-sm">
      <button type="button" className={btn} onClick={() => zoom(1)} aria-label="Приблизить">
        <Plus className="size-4" />
      </button>
      <button type="button" className={`${btn} border-t border-line`} onClick={() => zoom(-1)} aria-label="Отдалить">
        <Minus className="size-4" />
      </button>
    </div>
  )
}
