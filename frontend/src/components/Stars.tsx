import { Star } from 'lucide-react'
import { cn } from '@/lib/utils'

/** Звёзды рейтинга только для показа. Для выбора оценки — StarPicker */
export function Stars({ value, className }: { value: number; className?: string }) {
  return (
    <span className={cn('inline-flex items-center gap-0.5', className)} role="img" aria-label={`${value} из 5`}>
      {[1, 2, 3, 4, 5].map((n) => (
        <Star
          key={n}
          className={cn('size-4', n <= Math.round(value) ? 'fill-signal text-signal-dark' : 'text-line')}
          aria-hidden
        />
      ))}
    </span>
  )
}

export function StarPicker({ value, onChange }: { value: number; onChange: (v: number) => void }) {
  const labels = ['Ужасно', 'Плохо', 'Нормально', 'Хорошо', 'Отлично']
  return (
    <fieldset>
      <legend className="mb-1.5 text-sm font-medium">Оценка</legend>
      <div className="flex items-center gap-1">
        {[1, 2, 3, 4, 5].map((n) => (
          <label key={n} className="cursor-pointer rounded p-0.5 has-[:focus-visible]:outline-2 has-[:focus-visible]:outline-ink">
            <input
              type="radio"
              name="rating"
              value={n}
              checked={value === n}
              onChange={() => onChange(n)}
              className="sr-only"
              aria-label={`${n} из 5, ${labels[n - 1].toLowerCase()}`}
            />
            <Star className={cn('size-8', n <= value ? 'fill-signal text-signal-dark' : 'text-line')} aria-hidden />
          </label>
        ))}
        {value > 0 && <span className="ml-2 text-sm text-steel">{labels[value - 1]}</span>}
      </div>
    </fieldset>
  )
}
