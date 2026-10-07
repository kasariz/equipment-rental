import { ChevronLeft, ChevronRight } from 'lucide-react'
import { useCallback, useEffect, useRef, useState, type ReactNode } from 'react'
import { cn } from '@/lib/utils'

type Props = {
  children: ReactNode
  className?: string
  /** Фон под стрелками, чтобы контент плавно уходил под них */
  fadeFrom?: string
  label?: string
}

/**
 * Горизонтальная полоса для мыши, тачпада и пальца:
 * - на телефоне листается жестом;
 * - колесо мыши крутит полосу вбок, пока есть куда крутить, потом снова листает страницу;
 * - по краям появляются стрелки, если за краем что-то есть.
 */
export function HorizontalScroller({ children, className, fadeFrom = 'from-paper', label }: Props) {
  const ref = useRef<HTMLDivElement>(null)
  const [canLeft, setCanLeft] = useState(false)
  const [canRight, setCanRight] = useState(false)

  const update = useCallback(() => {
    const el = ref.current
    if (!el) return
    setCanLeft(el.scrollLeft > 1)
    setCanRight(el.scrollLeft + el.clientWidth < el.scrollWidth - 1)
  }, [])

  useEffect(() => {
    const el = ref.current
    if (!el) return
    update()
    const resize = new ResizeObserver(update)
    resize.observe(el)
    // Содержимое может поменяться (например, категории догрузились) — пересчитываем стрелки
    const mutations = new MutationObserver(update)
    mutations.observe(el, { childList: true, subtree: true })

    // Обработчик колеса вешаем сами: React добавляет wheel как passive, и preventDefault там не работает
    const onWheel = (e: WheelEvent) => {
      if (Math.abs(e.deltaY) <= Math.abs(e.deltaX)) return // тачпад уже листает вбок
      const atStart = el.scrollLeft <= 0
      const atEnd = el.scrollLeft + el.clientWidth >= el.scrollWidth - 1
      if ((e.deltaY < 0 && atStart) || (e.deltaY > 0 && atEnd)) return // дальше некуда — пусть листается страница
      e.preventDefault()
      el.scrollLeft += e.deltaY
    }
    el.addEventListener('wheel', onWheel, { passive: false })
    el.addEventListener('scroll', update, { passive: true })
    return () => {
      resize.disconnect()
      mutations.disconnect()
      el.removeEventListener('wheel', onWheel)
      el.removeEventListener('scroll', update)
    }
  }, [update])

  const scrollBy = (direction: 1 | -1) => {
    const el = ref.current
    if (el) el.scrollBy({ left: direction * el.clientWidth * 0.8, behavior: 'smooth' })
  }

  const arrow = 'absolute top-0 bottom-0 z-10 flex w-12 items-center to-transparent pointer-coarse:hidden'
  return (
    <div className="relative min-w-0">
      <div ref={ref} role="group" aria-label={label} className={cn('flex overflow-x-auto [scrollbar-width:none] [&::-webkit-scrollbar]:hidden', className)}>
        {children}
      </div>
      {canLeft && (
        <div className={cn(arrow, 'left-0 justify-start bg-gradient-to-r', fadeFrom)}>
          <button
            type="button"
            tabIndex={-1}
            aria-hidden
            onClick={() => scrollBy(-1)}
            className="flex size-8 items-center justify-center rounded-full border border-line bg-paper shadow-sm hover:border-ink"
          >
            <ChevronLeft className="size-4" />
          </button>
        </div>
      )}
      {canRight && (
        <div className={cn(arrow, 'right-0 justify-end bg-gradient-to-l', fadeFrom)}>
          <button
            type="button"
            tabIndex={-1}
            aria-hidden
            onClick={() => scrollBy(1)}
            className="flex size-8 items-center justify-center rounded-full border border-line bg-paper shadow-sm hover:border-ink"
          >
            <ChevronRight className="size-4" />
          </button>
        </div>
      )}
    </div>
  )
}
