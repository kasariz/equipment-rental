import { zodResolver } from '@hookform/resolvers/zod'
import { HardHat, Truck } from 'lucide-react'
import { Controller, useForm, useWatch } from 'react-hook-form'
import { Link, Navigate, useNavigate, useSearchParams } from 'react-router'
import { toast } from 'sonner'
import { z } from 'zod'
import { Button } from '@/components/ui/button'
import { Field } from '@/components/ui/field'
import { Input } from '@/components/ui/input'
import { PasswordInput } from '@/components/ui/password-input'
import { PhoneInput } from '@/components/ui/phone-input'
import { isCompletePhone } from '@/lib/phone'
import { useMe, useRegister } from '@/features/auth/api'
import { cn } from '@/lib/utils'
import { AuthShell } from './AuthShell'

const schema = z.object({
  role: z.enum(['client', 'owner']),
  full_name: z.string().trim().min(2, 'Введите имя и фамилию'),
  email: z.email('Введите email в формате name@example.ru'),
  phone: z.string().refine((v) => v === '' || isCompletePhone(v), 'Введите номер полностью: +7 и 10 цифр'),
  password: z.string().min(8, 'Пароль должен быть не короче 8 символов').max(128),
  consent: z.boolean().refine((v) => v, 'Без согласия зарегистрироваться нельзя'),
})
type FormValues = z.infer<typeof schema>

const roles = [
  {
    value: 'client',
    title: 'Арендую технику',
    text: 'Ищу технику для работ на своём объекте',
    Icon: HardHat,
  },
  {
    value: 'owner',
    title: 'Сдаю технику',
    text: 'Размещаю свою технику и принимаю заказы',
    Icon: Truck,
  },
] as const

export function RegisterPage() {
  const { data: user } = useMe()
  const registerUser = useRegister()
  const navigate = useNavigate()
  const [params] = useSearchParams()

  const { register, handleSubmit, control, formState: { errors } } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      role: params.get('role') === 'owner' ? 'owner' : 'client',
      full_name: '',
      email: '',
      phone: '',
      password: '',
      consent: false,
    },
  })
  const selectedRole = useWatch({ control, name: 'role' })

  if (user && !registerUser.isSuccess) {
    const isOwner = user.role === 'owner' || user.role === 'admin'
    return <Navigate to={isOwner ? '/my/equipment' : '/profile'} replace />
  }

  const onSubmit = ({ phone, consent, ...values }: FormValues) =>
    registerUser.mutate(
      { ...values, phone: phone || null, consent: consent as true },
      {
        onSuccess: () => {
          toast.success('Аккаунт создан')
          navigate('/profile', { replace: true })
        },
      },
    )

  return (
    <AuthShell title="Регистрация">
      <form onSubmit={handleSubmit(onSubmit)} noValidate className="flex flex-col gap-5">
        {registerUser.isError && (
          <div role="alert" className="rounded-md border border-danger/30 bg-danger/5 px-4 py-3 text-sm text-danger">
            {registerUser.error.message}
          </div>
        )}

        <fieldset className="grid gap-3 sm:grid-cols-2">
          <legend className="mb-2 text-sm font-medium">Как будете пользоваться сервисом</legend>
          {roles.map(({ value, title, text, Icon }) => (
            <label
              key={value}
              className={cn(
                'flex cursor-pointer flex-col gap-1.5 rounded-lg border-2 p-4 transition-colors has-[:focus-visible]:outline-2 has-[:focus-visible]:outline-offset-2 has-[:focus-visible]:outline-ink',
                selectedRole === value ? 'border-ink bg-signal/15' : 'border-line hover:border-steel',
              )}
            >
              <input type="radio" value={value} className="sr-only" {...register('role')} />
              <span className="flex items-center gap-2 font-medium">
                <Icon className="size-5" aria-hidden />
                {title}
              </span>
              <span className="text-sm text-steel">{text}</span>
            </label>
          ))}
        </fieldset>

        <Field id="full_name" label="Имя и фамилия" error={errors.full_name?.message}>
          <Input
            id="full_name"
            autoComplete="name"
            aria-invalid={!!errors.full_name}
            aria-describedby={errors.full_name ? 'full_name-error' : undefined}
            {...register('full_name')}
          />
        </Field>

        <Field id="email" label="Email" error={errors.email?.message}>
          <Input
            id="email"
            type="email"
            autoComplete="email"
            aria-invalid={!!errors.email}
            aria-describedby={errors.email ? 'email-error' : undefined}
            {...register('email')}
          />
        </Field>

        <Field
          id="phone"
          label="Телефон (необязательно)"
          hint={selectedRole === 'owner' ? 'По нему арендаторы свяжутся с вами' : 'По нему владелец техники свяжется с вами'}
          error={errors.phone?.message}
        >
          <Controller
            control={control}
            name="phone"
            render={({ field }) => (
              <PhoneInput
                id="phone"
                value={field.value}
                onChange={field.onChange}
                onBlur={field.onBlur}
                aria-invalid={!!errors.phone}
                aria-describedby={errors.phone ? 'phone-error' : 'phone-hint'}
              />
            )}
          />
        </Field>

        <Field id="password" label="Пароль" hint="Не короче 8 символов" error={errors.password?.message}>
          <PasswordInput
            id="password"
            autoComplete="new-password"
            aria-invalid={!!errors.password}
            aria-describedby={errors.password ? 'password-error' : 'password-hint'}
            {...register('password')}
          />
        </Field>

        <div className="flex flex-col gap-1.5">
          <label className="flex items-start gap-2.5 text-sm">
            <input
              type="checkbox"
              className="mt-0.5 size-4 shrink-0 accent-ink"
              aria-invalid={!!errors.consent}
              aria-describedby={errors.consent ? 'consent-error' : undefined}
              {...register('consent')}
            />
            <span>
              Даю согласие на обработку персональных данных (имя, email, телефон) в соответствии с{' '}
              <Link to="/privacy" target="_blank" className="font-medium underline underline-offset-4 hover:decoration-signal">
                политикой конфиденциальности
              </Link>
            </span>
          </label>
          {errors.consent && (
            <p id="consent-error" role="alert" className="text-sm text-danger">
              {errors.consent.message}
            </p>
          )}
        </div>

        <Button type="submit" size="lg" className="mt-2" disabled={registerUser.isPending}>
          {registerUser.isPending ? 'Создаём аккаунт…' : 'Создать аккаунт'}
        </Button>

        <p className="text-sm text-steel">
          Уже есть аккаунт?{' '}
          <Link to="/login" className="font-medium text-ink underline underline-offset-4 hover:decoration-signal">
            Войти
          </Link>
        </p>
      </form>
    </AuthShell>
  )
}
