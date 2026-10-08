import { useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { Field } from '@/components/ui/field'
import { Input } from '@/components/ui/input'
import { PasswordInput } from '@/components/ui/password-input'
import { useConfirmPasswordReset, useRequestPasswordReset, useSiteInfo } from '@/features/account/api'
import { AuthShell } from './AuthShell'

export function ForgotPasswordPage() {
  const [email, setEmail] = useState('')
  const request = useRequestPasswordReset()
  const { data: site } = useSiteInfo()

  if (request.isSuccess) {
    return (
      <AuthShell title="Проверьте почту и Telegram">
        <p className="text-steel">
          Если аккаунт с адресом <span className="text-ink">{email}</span> есть, мы отправили ссылку для смены пароля
          {site?.password_reset_by_email ? ' на почту' : ''} и в Telegram, если он подключён. Ссылка действует 30 минут.
        </p>
        <p className="mt-4 text-steel">Ничего не пришло? Свяжитесь с администратором сайта: он может выдать ссылку вручную.</p>
        <Button asChild variant="outline" className="mt-6">
          <Link to="/login">Вернуться ко входу</Link>
        </Button>
      </AuthShell>
    )
  }

  return (
    <AuthShell title="Восстановление пароля">
      <form
        className="flex flex-col gap-5"
        onSubmit={(e) => {
          e.preventDefault()
          request.mutate(email.trim())
        }}
      >
        <p className="text-steel">Укажите email, с которым регистрировались. Пришлём ссылку для смены пароля.</p>
        {request.isError && (
          <p role="alert" className="rounded-md border border-danger/30 bg-danger/5 px-4 py-3 text-sm text-danger">
            {request.error.message}
          </p>
        )}
        <Field id="email" label="Email">
          <Input id="email" type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} autoFocus />
        </Field>
        <Button type="submit" size="lg" disabled={request.isPending}>
          {request.isPending ? 'Отправляем…' : 'Получить ссылку'}
        </Button>
        <Link to="/login" className="text-sm font-medium underline underline-offset-4">
          Вспомнил пароль
        </Link>
      </form>
    </AuthShell>
  )
}

export function ResetPasswordPage() {
  const [params] = useSearchParams()
  const token = params.get('token') ?? ''
  const [password, setPassword] = useState('')
  const [repeat, setRepeat] = useState('')
  const [error, setError] = useState<string | null>(null)
  const confirm = useConfirmPasswordReset()
  const navigate = useNavigate()

  return (
    <AuthShell title="Новый пароль">
      <form
        className="flex flex-col gap-5"
        onSubmit={(e) => {
          e.preventDefault()
          if (password.length < 8) return setError('Пароль должен быть не короче 8 символов')
          if (password !== repeat) return setError('Пароли не совпадают')
          setError(null)
          confirm.mutate(
            { token, password },
            {
              onSuccess: () => {
                toast.success('Пароль изменён. Войдите с новым паролем')
                navigate('/login', { replace: true })
              },
            },
          )
        }}
      >
        {(error || confirm.isError) && (
          <p role="alert" className="rounded-md border border-danger/30 bg-danger/5 px-4 py-3 text-sm text-danger">
            {error ?? confirm.error?.message}
          </p>
        )}
        {!token && <p className="text-danger">В ссылке нет кода. Откройте ссылку из письма или сообщения целиком.</p>}
        <Field id="password" label="Новый пароль" hint="Не короче 8 символов">
          <PasswordInput id="password" autoComplete="new-password" value={password} onChange={(e) => setPassword(e.target.value)} />
        </Field>
        <Field id="repeat" label="Повторите пароль">
          <PasswordInput id="repeat" autoComplete="new-password" value={repeat} onChange={(e) => setRepeat(e.target.value)} />
        </Field>
        <Button type="submit" size="lg" disabled={!token || confirm.isPending}>
          {confirm.isPending ? 'Сохраняем…' : 'Сохранить пароль'}
        </Button>
        <p className="text-sm text-steel">После смены пароля мы выйдем из аккаунта на всех устройствах.</p>
      </form>
    </AuthShell>
  )
}
