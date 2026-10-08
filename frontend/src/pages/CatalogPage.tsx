import { List, LocateFixed, Map as MapIcon, Search, SlidersHorizontal, X } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { toast } from 'sonner'
import { EquipmentCard } from '@/components/EquipmentCard'
import { EquipmentMap } from '@/components/map/EquipmentMap'
import { PageSpinner } from '@/components/PageSpinner'
import { Button } from '@/components/ui/button'
import { HorizontalScroller } from '@/components/ui/horizontal-scroller'
import { Input } from '@/components/ui/input'
import { useCategories, useEquipmentList } from '@/features/catalog/api'
import { useCatalogFilters, type CatalogFilters } from '@/features/catalog/useCatalogFilters'
import { pluralize } from '@/lib/format'
import { cn } from '@/lib/utils'

const selectClass =
  'h-10 rounded-md border border-line bg-paper px-3 text-[15px] hover:border-steel focus-visible:border-ink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-signal'

/** Поиск с задержкой: запрос уходит, когда человек перестал печатать */
function SearchBox({ value, onChange }: { value: string; onChange: (v: string) => void }) {
  const [text, setText] = useState(value)
  const [prevValue, setPrevValue] = useState(value)
  if (value !== prevValue) {
    // Фильтры сбросили снаружи — подтягиваем текст в поле
    setPrevValue(value)
    setText(value)
  }
  useEffect(() => {
    if (text === value) return
    const t = setTimeout(() => onChange(text), 400)
    return () => clearTimeout(t)
  }, [text, value, onChange])

  return (
    <div className="relative">
      <Search className="pointer-events-none absolute top-1/2 left-3.5 size-4 -translate-y-1/2 text-steel" aria-hidden />
      <Input
        type="search"
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder="Название или марка, например JCB"
        aria-label="Поиск по названию"
        className="pl-10"
      />
    </div>
  )
}

function CategoryChips({ value, onChange }: { value: string; onChange: (slug: string) => void }) {
  const { data: categories } = useCategories()
  const chip = (active: boolean) =>
    cn(
      'shrink-0 rounded-full border px-3.5 py-1.5 text-sm transition-colors',
      active ? 'border-ink bg-ink text-paper' : 'border-line bg-paper hover:border-ink',
    )
  return (
    <HorizontalScroller className="gap-2" fadeFrom="from-concrete" label="Категория">
      <button type="button" className={chip(!value)} aria-pressed={!value} onClick={() => onChange('')}>
        Вся техника
      </button>
      {categories?.map((c) => (
        <button
          key={c.slug}
          type="button"
          className={chip(value === c.slug)}
          aria-pressed={value === c.slug}
          onClick={() => onChange(value === c.slug ? '' : c.slug)}
        >
          {c.name}
        </button>
      ))}
    </HorizontalScroller>
  )
}

function nowForInput() {
  const d = new Date()
  d.setMinutes(d.getMinutes() - d.getTimezoneOffset())
  return d.toISOString().slice(0, 16)
}

function MoreFilters({
  filters,
  update,
}: {
  filters: CatalogFilters
  update: (p: Partial<CatalogFilters>) => void
}) {
  const datesInvalid = filters.from && filters.to && new Date(filters.from) >= new Date(filters.to)
  return (
    <div className="grid gap-4 rounded-lg border border-line bg-paper p-4">
      <div className="grid gap-3 sm:grid-cols-2">
        <label className="flex flex-col gap-1.5 text-sm font-medium">
          Цена за час с оператором, до
          <Input
            type="number"
            inputMode="numeric"
            min={0}
            step={100}
            placeholder="Любая"
            value={filters.priceMax}
            onChange={(e) => update({ priceMax: e.target.value })}
            className="h-10"
          />
        </label>
      </div>
      <fieldset className="grid gap-3 sm:grid-cols-2">
        <legend className="mb-1.5 text-sm font-medium">Свободна в период</legend>
        <label className="flex flex-col gap-1 text-sm text-steel">
          С
          <Input type="datetime-local" min={nowForInput()} value={filters.from} onChange={(e) => update({ from: e.target.value })} className="h-10" />
        </label>
        <label className="flex flex-col gap-1 text-sm text-steel">
          По
          <Input type="datetime-local" min={filters.from || nowForInput()} value={filters.to} onChange={(e) => update({ to: e.target.value })} className="h-10" />
        </label>
        {datesInvalid && <p className="text-sm text-danger sm:col-span-2">Окончание должно быть позже начала</p>}
      </fieldset>
    </div>
  )
}

function NearMe({ filters, update }: { filters: CatalogFilters; update: (p: Partial<CatalogFilters>) => void }) {
  const [locating, setLocating] = useState(false)
  const hasPoint = Boolean(filters.lat && filters.lon)

  const locate = () => {
    if (!navigator.geolocation) {
      toast.error('Браузер не умеет определять местоположение')
      return
    }
    setLocating(true)
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setLocating(false)
        update({
          lat: pos.coords.latitude.toFixed(5),
          lon: pos.coords.longitude.toFixed(5),
          radius: filters.radius || '30',
          sort: 'distance',
        })
      },
      () => {
        setLocating(false)
        toast.error('Не удалось определить местоположение. Разрешите доступ к геопозиции в браузере')
      },
      { timeout: 10000 },
    )
  }

  if (!hasPoint) {
    return (
      <Button variant="outline" size="sm" onClick={locate} disabled={locating}>
        <LocateFixed />
        {locating ? 'Определяем…' : 'Рядом со мной'}
      </Button>
    )
  }

  return (
    <div className="flex items-center gap-1.5">
      <select
        aria-label="Радиус поиска"
        className={cn(selectClass, 'h-9 text-sm')}
        value={filters.radius}
        onChange={(e) => update({ radius: e.target.value })}
      >
        <option value="10">В радиусе 10 км</option>
        <option value="30">В радиусе 30 км</option>
        <option value="50">В радиусе 50 км</option>
        <option value="100">В радиусе 100 км</option>
        <option value="">Любое расстояние</option>
      </select>
      <Button
        variant="ghost"
        size="sm"
        aria-label="Не искать рядом со мной"
        onClick={() => update({ lat: '', lon: '', radius: '', sort: filters.sort === 'distance' ? 'new' : filters.sort })}
      >
        <X />
      </Button>
    </div>
  )
}

export function CatalogPage() {
  const { filters, update, reset, query, activeCount } = useCatalogFilters()
  const { data, isPending, isError, isFetching, refetch } = useEquipmentList(query)
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [hoveredId, setHoveredId] = useState<number | null>(null)
  const [showMore, setShowMore] = useState(Boolean(filters.priceMax || filters.from))
  const [mobileView, setMobileView] = useState<'list' | 'map'>('list')
  const cardRefs = useRef(new Map<number, HTMLAnchorElement>())

  const items = data?.items ?? []
  const total = data?.total ?? 0
  const hasPoint = Boolean(filters.lat && filters.lon)
  const userPoint: [number, number] | undefined = hasPoint ? [Number(filters.lat), Number(filters.lon)] : undefined
  const selectedItem = items.find((i) => i.id === selectedId)

  const selectFromMap = (id: number) => {
    setSelectedId(id)
    cardRefs.current.get(id)?.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
  }

  return (
    <div className="lg:grid lg:h-[calc(100svh-70px)] lg:grid-cols-[minmax(400px,480px)_minmax(0,1fr)]">
      {/* Левая колонка: фильтры и список */}
      <section className={cn('flex flex-col lg:overflow-y-auto', mobileView === 'map' && 'max-lg:hidden')} aria-label="Результаты поиска">
        <div className="flex flex-col gap-3 border-b border-line bg-concrete px-4 pt-5 pb-4">
          <h1 className="font-display text-2xl font-semibold tracking-tight">Каталог техники</h1>
          <SearchBox value={filters.q} onChange={(q) => update({ q })} />
          <CategoryChips value={filters.category} onChange={(category) => update({ category })} />
          <div className="flex flex-wrap items-center gap-2">
            <Button variant="outline" size="sm" aria-expanded={showMore} onClick={() => setShowMore((v) => !v)}>
              <SlidersHorizontal />
              Ещё фильтры
            </Button>
            <NearMe filters={filters} update={update} />
            {filters.area && (
              <Button variant="dark" size="sm" onClick={() => update({ area: '' })} aria-label="Искать по всей карте">
                В области карты
                <X />
              </Button>
            )}
          </div>
          {showMore && <MoreFilters filters={filters} update={update} />}
        </div>

        <div className="flex items-center justify-between gap-3 px-4 pt-4 pb-2">
          <p className="text-sm text-steel" aria-live="polite">
            {isPending ? 'Ищем технику…' : `Найдено ${total} ${pluralize(total, ['единица', 'единицы', 'единиц'])}`}
          </p>
          <select
            aria-label="Сортировка"
            className={cn(selectClass, 'h-9 text-sm')}
            value={query.sort}
            onChange={(e) => update({ sort: e.target.value as CatalogFilters['sort'] })}
          >
            <option value="new">Сначала новые</option>
            <option value="price_asc">Сначала дешевле</option>
            <option value="price_desc">Сначала дороже</option>
            {hasPoint && <option value="distance">Сначала ближе</option>}
          </select>
        </div>

        <div className={cn('flex flex-col gap-1 px-2 pb-24 lg:pb-6', isFetching && !isPending && 'opacity-60 transition-opacity')}>
          {isPending && <PageSpinner />}
          {isError && (
            <div className="m-2 rounded-lg border border-danger/30 bg-danger/5 p-4 text-sm">
              <p className="text-danger">Не удалось загрузить каталог.</p>
              <Button variant="outline" size="sm" className="mt-3" onClick={() => refetch()}>
                Повторить
              </Button>
            </div>
          )}
          {!isPending && !isError && items.length === 0 && (
            <div className="m-2 rounded-lg border border-dashed border-line p-6">
              <p className="font-medium">Под эти условия техники не нашлось</p>
              <p className="mt-1 text-sm text-steel">
                Попробуйте убрать часть фильтров, расширить радиус или выбрать другие даты.
              </p>
              {activeCount > 0 && (
                <Button variant="outline" size="sm" className="mt-4" onClick={reset}>
                  Сбросить фильтры
                </Button>
              )}
            </div>
          )}
          {items.map((item) => (
            <EquipmentCard
              key={item.id}
              item={item}
              active={item.id === selectedId || item.id === hoveredId}
              onHover={setHoveredId}
              ref={(el) => {
                if (el) cardRefs.current.set(item.id, el)
                else cardRefs.current.delete(item.id)
              }}
            />
          ))}
        </div>
      </section>

      {/* Правая колонка: карта */}
      <section
        className={cn(
          // высота шапки: 70px, на телефоне плюс строка навигации
          'relative h-[calc(100svh-111px)] md:max-lg:h-[calc(100svh-70px)] lg:h-full',
          mobileView === 'list' && 'max-lg:hidden',
        )}
        aria-label="Карта"
      >
        <EquipmentMap
          items={items}
          selectedId={hoveredId ?? selectedId}
          onSelect={selectFromMap}
          userPoint={userPoint}
          areaActive={Boolean(filters.area)}
          onSearchArea={(area) => update({ area: area.map((n) => n.toFixed(5)).join(',') })}
        />
        {/* На телефоне выбранная на карте техника показывается карточкой снизу */}
        {selectedItem && (
          <div className="absolute inset-x-3 bottom-20 z-[1000] lg:hidden">
            <EquipmentCard item={selectedItem} />
          </div>
        )}
      </section>

      {/* Переключатель «Список / Карта» на телефоне */}
      <div className="fixed bottom-5 left-1/2 z-[1100] -translate-x-1/2 lg:hidden">
        <Button variant="dark" className="shadow-lg" onClick={() => setMobileView((v) => (v === 'list' ? 'map' : 'list'))}>
          {mobileView === 'list' ? <MapIcon /> : <List />}
          {mobileView === 'list' ? 'Показать на карте' : 'Показать списком'}
        </Button>
      </div>
    </div>
  )
}
