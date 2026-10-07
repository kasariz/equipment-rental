import { Construction } from 'lucide-react'
import { cn } from '@/lib/utils'

/** Фото техники или нейтральная заглушка, если владелец ещё не загрузил снимки */
export function EquipmentImage({ src, alt, className }: { src?: string | null; alt: string; className?: string }) {
  if (src) {
    return <img src={src} alt={alt} loading="lazy" className={cn('object-cover', className)} />
  }
  return (
    <div className={cn('flex items-center justify-center bg-concrete text-steel/50', className)} role="img" aria-label={`${alt}: фото нет`}>
      <Construction className="size-1/4 max-h-12 max-w-12" strokeWidth={1.5} />
    </div>
  )
}
