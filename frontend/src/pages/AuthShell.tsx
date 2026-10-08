import type { ReactNode } from 'react'

const steps = [
  'Найдите технику на карте рядом с вашим объектом',
  'Выберите время: от нескольких часов до смены и дольше',
  'Владелец перезвонит и подтвердит бронь, техника приедет с оператором',
]

/** Общая раскладка страниц входа и регистрации: слева о сервисе, справа форма. */
export function AuthShell({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="mx-auto grid max-w-6xl gap-0 px-4 py-8 sm:px-6 lg:grid-cols-[5fr_6fr] lg:py-14">
      <aside className="relative hidden overflow-hidden rounded-l-xl bg-ink p-10 text-paper lg:block">
        <p className="font-display text-2xl leading-snug font-semibold">
          Техника на объект без обзвона объявлений
        </p>
        <ol className="mt-10 flex flex-col gap-6">
          {steps.map((text, i) => (
            <li key={text} className="flex gap-4">
              <span className="font-display flex size-8 shrink-0 items-center justify-center rounded-full bg-signal text-sm font-bold text-ink">
                {i + 1}
              </span>
              <span className="pt-1 text-paper/85">{text}</span>
            </li>
          ))}
        </ol>
        <div className="hazard-stripe absolute inset-x-0 bottom-0 h-3" aria-hidden />
      </aside>

      <section className="rounded-xl border border-line bg-paper p-6 sm:p-10 lg:rounded-l-none lg:border-l-0">
        <div className="mx-auto max-w-md">
          <h1 className="font-display text-3xl font-semibold tracking-tight">{title}</h1>
          <div className="mt-8">{children}</div>
        </div>
      </section>
    </div>
  )
}
