import { zodResolver } from '@hookform/resolvers/zod'
import { useForm } from 'react-hook-form'
import { Link, Navigate, useLocation, useNavigate } from 'react-router'
import { z } from 'zod'
import { Button } from '@/components/ui/button'
import { Field } from '@/components/ui/field'
import { Input } from '@/components/ui/input'
import { PasswordInput } from '@/components/ui/password-input'
import { useLogin, useMe } from '@/features/auth/api'
import { AuthShell } from './AuthShell'

const schema = z.object({
  email: z.email('Введите email в формате name@example.ru'),
  password: z.string().min(1, 'Введите пароль'),
})
type FormValues = z.infer<typeof schema>

export function LoginPage() {
  const { data: user } = useMe()
  const login = useLogin()
  const navigate = useNavigate()
  const location = useLocation()
  const from = (location.state as { from?: string } | null)?.from ?? '/'

  const { register, handleSubmit, formState: { errors } } = useForm<FormValues>({
    resolver: zodResolver(schema),
  })

  if (user && !login.isSuccess) return <Navigate to="/profile" replace />

  const onSubmit = (values: FormValues) =>
    login.mutate(values, { onSuccess: () => navigate(from, { replace: true }) })

  return (
    <AuthShell title="Вход">
      <form onSubmit={handleSubmit(onSubmit)} noValidate className="flex flex-col gap-5">
        {login.isError && (
          <div role="alert" className="rounded-md border border-danger/30 bg-danger/5 px-4 py-3 text-sm text-danger">
            {login.error.message}
          </div>
        )}

        <Field id="email" label="Email" error={errors.email?.message}>
          <Input
            id="email"
            type="email"
            autoComplete="email"
            autoFocus
            aria-invalid={!!errors.email}
            aria-describedby={errors.email ? 'email-error' : undefined}
            {...register('email')}
          />
        </Field>

        <Field id="password" label="Пароль" error={errors.password?.message}>
          <PasswordInput
            id="password"
            autoComplete="current-password"
            aria-invalid={!!errors.password}
            aria-describedby={errors.password ? 'password-error' : undefined}
            {...register('password')}
          />
        </Field>

        <Button type="submit" size="lg" className="mt-2" disabled={login.isPending}>
          {login.isPending ? 'Входим…' : 'Войти'}
        </Button>

        <Link to="/forgot-password" className="self-start text-sm font-medium underline underline-offset-4 hover:decoration-signal">
          Забыли пароль?
        </Link>

        <p className="text-sm text-steel">
          Нет аккаунта?{' '}
          <Link to="/register" className="font-medium text-ink underline underline-offset-4 hover:decoration-signal">
            Зарегистрироваться
          </Link>
        </p>
      </form>
    </AuthShell>
  )
}
