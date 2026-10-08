import type { ComponentProps } from 'react'
import { nextPhoneValue } from '@/lib/phone'
import { Input } from './input'

type Props = Omit<ComponentProps<'input'>, 'value' | 'onChange' | 'type'> & {
  value: string
  onChange: (value: string) => void
}

/** Поле телефона с маской: 8 сразу превращается в +7, больше 10 цифр после кода не ввести */
export function PhoneInput({ value, onChange, ...props }: Props) {
  return (
    <Input
      {...props}
      type="tel"
      inputMode="tel"
      autoComplete="tel"
      placeholder="+7 (900) 123-45-67"
      value={value}
      onChange={(e) => onChange(nextPhoneValue(value, e.target.value))}
    />
  )
}
