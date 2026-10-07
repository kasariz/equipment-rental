import { Link } from 'react-router'

export function Logo() {
  return (
    <Link to="/" className="flex items-center gap-2.5 rounded-sm" aria-label="Ковш, на главную">
      <svg viewBox="0 0 32 32" className="size-8" aria-hidden>
        <rect width="32" height="32" rx="6" fill="var(--color-ink)" />
        <path d="M7 11h18l-3 12a2 2 0 0 1-2 1.5h-8A2 2 0 0 1 10 23z" fill="var(--color-signal)" />
        <path
          d="M10 24.5l1.5 3M16 24.5v3M22 24.5l-1.5 3"
          stroke="var(--color-signal)"
          strokeWidth="2"
          strokeLinecap="round"
        />
      </svg>
      <span className="font-display text-xl font-bold tracking-tight">Ковш</span>
    </Link>
  )
}
