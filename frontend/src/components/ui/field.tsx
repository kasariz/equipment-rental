import type { ReactNode } from 'react'
import { Label } from './label'

type FieldProps = {
  id: string
  label: string
  hint?: string
  error?: string
  children: ReactNode
}

/** Подпись + поле + подсказка или ошибка. Ошибку экранные дикторы читают через aria-describedby. */
export function Field({ id, label, hint, error, children }: FieldProps) {
  return (
    <div className="flex flex-col gap-1.5">
      <Label htmlFor={id}>{label}</Label>
      {children}
      {error ? (
        <p id={`${id}-error`} role="alert" className="text-sm text-danger">
          {error}
        </p>
      ) : hint ? (
        <p id={`${id}-hint`} className="text-sm text-steel">
          {hint}
        </p>
      ) : null}
    </div>
  )
}
