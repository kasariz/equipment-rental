import { ChevronLeft, ChevronRight, Pencil, Plus, Search, Trash2, UserRound, X } from 'lucide-react'
import { useState, type ReactNode } from 'react'
import { Link } from 'react-router'
import { toast } from 'sonner'
import type { BookingStatus, Category, EquipmentStatus, UserRole } from '@/api/client'
import { PageSpinner } from '@/components/PageSpinner'
import { Stars } from '@/components/Stars'
import { Button } from '@/components/ui/button'
import { ConfirmDialog } from '@/components/ui/confirm-dialog'
import { Input } from '@/components/ui/input'
import {
  useAdminBookings,
  useAdminDelete,
  useAdminEquipment,
  useAdminReviews,
  useAdminUsers,
  useSaveCategory,
  type TemplateItem,
} from '@/features/admin/api'
import { roleLabels, useMe } from '@/features/auth/api'
import { useCategories } from '@/features/catalog/api'
import { useDebounced } from '@/hooks/useDebounced'
import { formatPeriod } from '@/lib/dates'
import { bookingStatusForOwner, bookingStatusStyle, formatRub, statusLabels } from '@/lib/format'
import { formatPhone } from '@/lib/phone'
import { cn } from '@/lib/utils'

const PAGE_SIZE = 50
const dateFmt = new Intl.DateTimeFormat('ru-RU', { day: 'numeric', month: 'short', year: 'numeric' })
const selectClass =
  'h-10 rounded-md border border-line bg-paper px-3 text-[15px] hover:border-steel focus-visible:border-ink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-signal'

type TabKey = 'users' | 'bookings' | 'equipment' | 'reviews' | 'categories'
/** Выбранный аккаунт: остальные вкладки показывают только его записи */
type Account = { id: number; name: string } | null

// ---------- общие детали ----------

function DeleteButton({ what, description, onConfirm }: { what: string; description: string; onConfirm: () => void }) {
  return (
    <ConfirmDialog
      title={`Удалить ${what}?`}
      description={description}
      confirmLabel="Удалить насовсем"
      onConfirm={onConfirm}
      trigger={
        <Button variant="ghost" size="sm" aria-label={`Удалить ${what}`} className="text-danger hover:bg-danger/10">
          <Trash2 />
        </Button>
      }
    />
  )
}

function useDelete(entity: Parameters<typeof useAdminDelete>[0], done: string) {
  const del = useAdminDelete(entity)
  return (id: number) => del.mutate(id, { onSuccess: () => toast.success(done), onError: (e) => toast.error(e.message) })
}

function Row({ children, actions }: { children: ReactNode; actions?: ReactNode }) {
  return (
    <li className="grid grid-cols-[minmax(0,1fr)_auto] items-start gap-3 px-4 py-3">
      <div className="min-w-0 text-[15px]">{children}</div>
      <div className="flex gap-1">{actions}</div>
    </li>
  )
}

function SearchInput({ value, onChange, placeholder }: { value: string; onChange: (v: string) => void; placeholder: string }) {
  return (
    <div className="relative min-w-56 flex-1">
      <Search className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-steel" aria-hidden />
      <Input
        type="search"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        aria-label={placeholder}
        className="h-10 pl-9"
      />
    </div>
  )
}

function AccountChip({ account, onClear }: { account: Account; onClear: () => void }) {
  if (!account) return null
  return (
    <span className="inline-flex h-10 items-center gap-2 rounded-md bg-ink px-3 text-sm text-paper">
      <UserRound className="size-4" aria-hidden />
      {account.name}
      <button type="button" onClick={onClear} aria-label="Показать все аккаунты" className="rounded-sm hover:text-signal">
        <X className="size-4" />
      </button>
    </span>
  )
}

/** Список с подписью «Показано 51–100 из 830» и кнопками страниц */
function PagedList({
  loading,
  fetching,
  total,
  offset,
  onOffset,
  empty,
  children,
}: {
  loading: boolean
  fetching: boolean
  total: number
  offset: number
  onOffset: (offset: number) => void
  empty: string
  children: ReactNode[]
}) {
  if (loading) return <PageSpinner />
  if (total === 0) return <p className="mt-6 text-steel">{empty}</p>
  const to = Math.min(offset + PAGE_SIZE, total)
  return (
    <>
      <ul className={cn('mt-4 divide-y divide-line rounded-xl border border-line bg-paper', fetching && 'opacity-60')}>
        {children}
      </ul>
      <div className="mt-3 flex items-center justify-between gap-3 text-sm text-steel">
        <span aria-live="polite">
          Показано {offset + 1}–{to} из {total}
        </span>
        <div className="flex gap-1">
          <Button variant="outline" size="sm" disabled={offset === 0} onClick={() => onOffset(Math.max(0, offset - PAGE_SIZE))}>
            <ChevronLeft />
            Назад
          </Button>
          <Button variant="outline" size="sm" disabled={to >= total} onClick={() => onOffset(offset + PAGE_SIZE)}>
            Вперёд
            <ChevronRight />
          </Button>
        </div>
      </div>
    </>
  )
}

/** Фильтры вкладки + сброс страницы на первую при любом изменении фильтра */
function useFilters<T extends object>(initial: T) {
  const [filters, setFilters] = useState(initial)
  const [offset, setOffset] = useState(0)
  const update = (patch: Partial<T>) => {
    setFilters((f) => ({ ...f, ...patch }))
    setOffset(0)
  }
  return { filters, update, offset, setOffset }
}

// ---------- вкладки ----------

function UsersTab({ onOpenAccount }: { onOpenAccount: (account: Account, tab: TabKey) => void }) {
  const { filters, update, offset, setOffset } = useFilters({ q: '', role: '' as UserRole | '' })
  const q = useDebounced(filters.q)
  const { data, isPending, isFetching } = useAdminUsers({
    q: q || undefined,
    role: filters.role || undefined,
    limit: PAGE_SIZE,
    offset,
  })
  const { data: me } = useMe()
  const remove = useDelete('users', 'Пользователь удалён')

  return (
    <>
      <div className="mt-6 flex flex-wrap gap-2">
        <SearchInput value={filters.q} onChange={(v) => update({ q: v })} placeholder="Имя, email или телефон" />
        <select aria-label="Роль" className={selectClass} value={filters.role} onChange={(e) => update({ role: e.target.value as UserRole | '' })}>
          <option value="">Все роли</option>
          <option value="client">Арендаторы</option>
          <option value="owner">Владельцы</option>
          <option value="admin">Администраторы</option>
        </select>
      </div>
      <PagedList loading={isPending} fetching={isFetching} total={data?.total ?? 0} offset={offset} onOffset={setOffset} empty="Никого не нашлось">
        {(data?.items ?? []).map((u) => {
          const account = { id: u.id, name: u.full_name }
          return (
            <Row
              key={u.id}
              actions={
                u.id === me?.id ? null : (
                  <DeleteButton
                    what={u.full_name}
                    description={`Вместе с аккаунтом удалятся его техника (${u.equipment_count}), брони (${u.bookings_count}) и отзывы.`}
                    onConfirm={() => remove(u.id)}
                  />
                )
              }
            >
              <span className="font-medium">{u.full_name}</span>
              <span className="ml-2 text-sm text-steel">{roleLabels[u.role]}</span>
              <p className="text-sm break-words text-steel">
                {u.email}
                {u.phone ? `, ${formatPhone(u.phone)}` : ''}. С {dateFmt.format(new Date(u.created_at))}
              </p>
              <p className="mt-1 flex flex-wrap gap-x-4 text-sm">
                <button type="button" className="underline underline-offset-4 hover:decoration-signal" onClick={() => onOpenAccount(account, 'bookings')}>
                  Брони: {u.bookings_count}
                </button>
                {u.equipment_count > 0 && (
                  <button type="button" className="underline underline-offset-4 hover:decoration-signal" onClick={() => onOpenAccount(account, 'equipment')}>
                    Техника: {u.equipment_count}
                  </button>
                )}
                <button type="button" className="underline underline-offset-4 hover:decoration-signal" onClick={() => onOpenAccount(account, 'reviews')}>
                  Отзывы
                </button>
              </p>
            </Row>
          )
        })}
      </PagedList>
    </>
  )
}

const BOOKING_STATUS_GROUPS: Record<string, BookingStatus[] | undefined> = {
  all: undefined,
  current: ['pending', 'confirmed', 'active'],
  pending: ['pending'],
  archive: ['completed', 'cancelled', 'rejected', 'expired'],
}

function BookingsTab({ account, onClearAccount }: { account: Account; onClearAccount: () => void }) {
  const { filters, update, offset, setOffset } = useFilters({ q: '', group: 'all' })
  const q = useDebounced(filters.q)
  const { data, isPending, isFetching } = useAdminBookings({
    q: q || undefined,
    status: BOOKING_STATUS_GROUPS[filters.group],
    user_id: account?.id,
    limit: PAGE_SIZE,
    offset,
  })
  const remove = useDelete('bookings', 'Бронь удалена')

  return (
    <>
      <div className="mt-6 flex flex-wrap gap-2">
        <AccountChip account={account} onClear={onClearAccount} />
        <SearchInput value={filters.q} onChange={(v) => update({ q: v })} placeholder="Техника, клиент, email или № брони" />
        <select aria-label="Статус" className={selectClass} value={filters.group} onChange={(e) => update({ group: e.target.value })}>
          <option value="all">Все статусы</option>
          <option value="current">Текущие</option>
          <option value="pending">Ждут звонка</option>
          <option value="archive">Архив</option>
        </select>
      </div>
      <PagedList loading={isPending} fetching={isFetching} total={data?.total ?? 0} offset={offset} onOffset={setOffset} empty="Броней не нашлось">
        {(data?.items ?? []).map((b) => (
          <Row
            key={b.id}
            actions={
              <DeleteButton
                what={`бронь №${b.id}`}
                description="Бронь исчезнет и у клиента, и у владельца, в архив не попадёт. Занятое время освободится."
                onConfirm={() => remove(b.id)}
              />
            }
          >
            <span className={cn('mr-2 rounded-full px-2 py-0.5 text-xs font-medium', bookingStatusStyle[b.status])}>
              {bookingStatusForOwner[b.status]}
            </span>
            <span className="mr-2 text-sm text-steel">№{b.id}</span>
            <Link to={`/equipment/${b.equipment.id}`} className="font-medium hover:underline">
              {b.equipment.name}
            </Link>
            <p className="text-sm text-steel">
              {formatPeriod(b.start, b.end)}, {formatRub(b.total_price)}. Клиент: {b.client?.full_name},{' '}
              {formatPhone(b.contact_phone)}
            </p>
          </Row>
        ))}
      </PagedList>
    </>
  )
}

function EquipmentTab({ account, onClearAccount }: { account: Account; onClearAccount: () => void }) {
  const { data: categories } = useCategories()
  const { filters, update, offset, setOffset } = useFilters({ q: '', status: '' as EquipmentStatus | '', category: '' })
  const q = useDebounced(filters.q)
  const { data, isPending, isFetching } = useAdminEquipment({
    q: q || undefined,
    status: filters.status || undefined,
    category: filters.category || undefined,
    user_id: account?.id,
    limit: PAGE_SIZE,
    offset,
  })
  const remove = useDelete('equipment', 'Техника удалена')

  return (
    <>
      <div className="mt-6 flex flex-wrap gap-2">
        <AccountChip account={account} onClear={onClearAccount} />
        <SearchInput value={filters.q} onChange={(v) => update({ q: v })} placeholder="Название техники" />
        <select aria-label="Категория" className={selectClass} value={filters.category} onChange={(e) => update({ category: e.target.value })}>
          <option value="">Все категории</option>
          {categories?.map((c) => (
            <option key={c.slug} value={c.slug}>
              {c.name}
            </option>
          ))}
        </select>
        <select aria-label="Статус" className={selectClass} value={filters.status} onChange={(e) => update({ status: e.target.value as EquipmentStatus | '' })}>
          <option value="">Любой статус</option>
          {(Object.keys(statusLabels) as EquipmentStatus[]).map((s) => (
            <option key={s} value={s}>
              {statusLabels[s]}
            </option>
          ))}
        </select>
      </div>
      <PagedList loading={isPending} fetching={isFetching} total={data?.total ?? 0} offset={offset} onOffset={setOffset} empty="Техники не нашлось">
        {(data?.items ?? []).map((e) => (
          <Row
            key={e.id}
            actions={
              <DeleteButton
                what={`«${e.name}»`}
                description="Удалятся объявление, фото и все брони этой техники, включая активные."
                onConfirm={() => remove(e.id)}
              />
            }
          >
            <Link to={`/equipment/${e.id}`} className="font-medium hover:underline">
              {e.name}
            </Link>
            <p className="text-sm text-steel">
              {e.category}, {statusLabels[e.status as EquipmentStatus].toLowerCase()}. Владелец: {e.owner_name} ({e.owner_email})
            </p>
          </Row>
        ))}
      </PagedList>
    </>
  )
}

function ReviewsTab({ account, onClearAccount }: { account: Account; onClearAccount: () => void }) {
  const { filters, update, offset, setOffset } = useFilters({ direction: '', maxRating: '' })
  const { data, isPending, isFetching } = useAdminReviews({
    direction: (filters.direction || undefined) as 'about_owner' | 'about_renter' | undefined,
    max_rating: filters.maxRating ? Number(filters.maxRating) : undefined,
    user_id: account?.id,
    limit: PAGE_SIZE,
    offset,
  })
  const remove = useDelete('reviews', 'Отзыв удалён')

  return (
    <>
      <div className="mt-6 flex flex-wrap gap-2">
        <AccountChip account={account} onClear={onClearAccount} />
        <select aria-label="О ком отзыв" className={selectClass} value={filters.direction} onChange={(e) => update({ direction: e.target.value })}>
          <option value="">О владельцах и арендаторах</option>
          <option value="about_owner">О владельцах</option>
          <option value="about_renter">Об арендаторах</option>
        </select>
        <select aria-label="Оценка" className={selectClass} value={filters.maxRating} onChange={(e) => update({ maxRating: e.target.value })}>
          <option value="">Любая оценка</option>
          <option value="2">Только плохие (1–2)</option>
          <option value="3">До 3 включительно</option>
        </select>
      </div>
      <PagedList loading={isPending} fetching={isFetching} total={data?.total ?? 0} offset={offset} onOffset={setOffset} empty="Отзывов не нашлось">
        {(data?.items ?? []).map((r) => (
          <Row
            key={r.id}
            actions={<DeleteButton what="отзыв" description="Отзыв пропадёт, рейтинг пересчитается." onConfirm={() => remove(r.id)} />}
          >
            <Stars value={r.rating} />{' '}
            <span className="text-sm text-steel">
              {r.direction === 'about_owner' ? 'о владельце' : 'об арендаторе'} {r.subject_name}, от {r.author_name}. Аренда:{' '}
              {r.equipment_name}
            </span>
            {r.text && <p className="mt-1 break-words whitespace-pre-line">{r.text}</p>}
          </Row>
        ))}
      </PagedList>
    </>
  )
}

/** Шаблон характеристик в текстовом поле: «Грузоподъёмность | 20 т» — по строке на характеристику */
function templateToText(items: TemplateItem[]): string {
  return items.map((i) => (i.example ? `${i.name} | ${i.example}` : i.name)).join('\n')
}

function textToTemplate(text: string): TemplateItem[] {
  return text
    .split('\n')
    .map((line) => {
      const [name, ...rest] = line.split('|')
      return { name: name.trim(), example: rest.join('|').trim() || null }
    })
    .filter((i) => i.name)
}

function CategoryEditor({ category, onDone }: { category?: Category; onDone: () => void }) {
  const [name, setName] = useState(category?.name ?? '')
  const [template, setTemplate] = useState(templateToText((category?.spec_template ?? []) as TemplateItem[]))
  const save = useSaveCategory()
  return (
    <form
      className="grid gap-3 rounded-xl border border-line bg-paper p-4"
      onSubmit={(e) => {
        e.preventDefault()
        save.mutate(
          { id: category?.id, name: name.trim(), specTemplate: textToTemplate(template) },
          {
            onSuccess: () => {
              toast.success(category ? 'Категория сохранена' : 'Категория добавлена')
              onDone()
            },
            onError: (err) => toast.error(err.message),
          },
        )
      }}
    >
      <label className="flex flex-col gap-1.5 text-sm font-medium">
        Название
        <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="Бетоносмесители" required minLength={2} />
      </label>
      <label className="flex flex-col gap-1.5 text-sm font-medium">
        Характеристики: по одной в строке, пример значения — после вертикальной черты
        <textarea
          value={template}
          onChange={(e) => setTemplate(e.target.value)}
          rows={7}
          placeholder={'Объём барабана | 9 м³\nКолёсная формула | 6×4\nВысота выгрузки | 1,5 м'}
          className="rounded-md border border-line bg-paper px-3 py-2 font-mono text-sm font-normal focus-visible:border-ink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-signal"
        />
      </label>
      <div className="flex gap-2">
        <Button type="submit" disabled={save.isPending}>
          {category ? 'Сохранить' : 'Добавить'}
        </Button>
        <Button type="button" variant="ghost" onClick={onDone}>
          Отмена
        </Button>
      </div>
    </form>
  )
}

function CategoriesTab() {
  const { data, isPending } = useCategories()
  const remove = useDelete('categories', 'Категория удалена')
  const [editing, setEditing] = useState<number | 'new' | null>(null)
  if (isPending) return <PageSpinner />
  return (
    <div className="mt-6">
      {editing === 'new' ? (
        <CategoryEditor onDone={() => setEditing(null)} />
      ) : (
        <Button onClick={() => setEditing('new')}>
          <Plus />
          Добавить категорию
        </Button>
      )}
      <ul className="mt-4 divide-y divide-line rounded-xl border border-line bg-paper">
        {(data ?? []).map((c) =>
          editing === c.id ? (
            <li key={c.id} className="p-3">
              <CategoryEditor category={c} onDone={() => setEditing(null)} />
            </li>
          ) : (
            <Row
              key={c.id}
              actions={
                <>
                  <Button variant="ghost" size="sm" aria-label={`Изменить ${c.name}`} onClick={() => setEditing(c.id)}>
                    <Pencil />
                  </Button>
                  <DeleteButton
                    what={`категорию «${c.name}»`}
                    description="Удалить можно только пустую категорию: если в ней есть техника, сервер откажет."
                    onConfirm={() => remove(c.id)}
                  />
                </>
              }
            >
              <span className="font-medium">{c.name}</span>
              <p className="text-sm text-steel">
                {c.spec_template.length
                  ? c.spec_template.map((t) => (t.example ? `${t.name} (${t.example})` : t.name)).join(', ')
                  : 'Без шаблона характеристик'}
              </p>
            </Row>
          ),
        )}
      </ul>
    </div>
  )
}

const TABS: { key: TabKey; label: string }[] = [
  { key: 'users', label: 'Пользователи' },
  { key: 'bookings', label: 'Брони' },
  { key: 'equipment', label: 'Техника' },
  { key: 'reviews', label: 'Отзывы' },
  { key: 'categories', label: 'Категории' },
]

export function AdminPage() {
  const [tab, setTab] = useState<TabKey>('users')
  const [account, setAccount] = useState<Account>(null)
  const clearAccount = () => setAccount(null)

  return (
    <div className="mx-auto max-w-5xl px-4 py-10 sm:px-6 sm:py-14">
      <h1 className="font-display text-3xl font-semibold tracking-tight">Администрирование</h1>
      <p className="mt-2 max-w-prose text-steel">
        Найдите аккаунт во вкладке «Пользователи» и откройте его брони, технику или отзывы. Удаление здесь окончательное:
        записи не попадают в архив.
      </p>
      <div className="-mx-4 mt-8 flex gap-1 overflow-x-auto border-b border-line px-4 [scrollbar-width:none]" role="tablist">
        {TABS.map((t) => (
          <button
            key={t.key}
            type="button"
            role="tab"
            aria-selected={tab === t.key}
            onClick={() => setTab(t.key)}
            className={cn(
              '-mb-px shrink-0 border-b-[3px] px-3 py-2.5 text-[15px] whitespace-nowrap transition-colors',
              tab === t.key ? 'border-signal font-medium text-ink' : 'border-transparent text-steel hover:text-ink',
            )}
          >
            {t.label}
          </button>
        ))}
      </div>
      <div role="tabpanel">
        {tab === 'users' && (
          <UsersTab
            onOpenAccount={(a, next) => {
              setAccount(a)
              setTab(next)
            }}
          />
        )}
        {tab === 'bookings' && <BookingsTab key={account?.id ?? 'all'} account={account} onClearAccount={clearAccount} />}
        {tab === 'equipment' && <EquipmentTab key={account?.id ?? 'all'} account={account} onClearAccount={clearAccount} />}
        {tab === 'reviews' && <ReviewsTab key={account?.id ?? 'all'} account={account} onClearAccount={clearAccount} />}
        {tab === 'categories' && <CategoriesTab />}
      </div>
    </div>
  )
}
