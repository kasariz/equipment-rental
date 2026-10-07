import type { ComponentProps } from 'react'
import { cn } from '@/lib/utils'

export function Input({ className, ...props }: ComponentProps<'input'>) {
  return (
    <input
      className={cn(
        'h-11 w-full rounded-md border border-line bg-paper px-3.5 text-[15px] text-ink placeholder:text-steel/70',
        'transition-colors hover:border-steel focus-visible:border-ink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-signal',
        'aria-invalid:border-danger aria-invalid:ring-danger/20',
        className,
      )}
      {...props}
    />
  )
}
