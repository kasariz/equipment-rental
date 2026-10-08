import { LoaderCircle, MapPin } from 'lucide-react'
import { useEffect, useId, useRef, useState } from 'react'
import { Input } from '@/components/ui/input'
import { searchAddress, useGeoStatus, type GeoSuggestion, type PickedAddress } from '@/features/geo/api'
import { cn } from '@/lib/utils'

type Props = {
  id: string
  value: PickedAddress | null
  onChange: (value: PickedAddress | null) => void
  placeholder?: string
  invalid?: boolean
  describedBy?: string
}

/**
 * Адрес только из подсказок геокодера: так в базу не попадёт «где-то за гаражами».
 * Если геокодер на сервере не настроен, поле работает как обычное.
 */
export function AddressInput({ id, value, onChange, placeholder, invalid, describedBy }: Props) {
  const { data: geo } = useGeoStatus()
  const listId = useId()
  const [text, setText] = useState(value?.address ?? '')
  const [prevAddress, setPrevAddress] = useState(value?.address)
  const [items, setItems] = useState<GeoSuggestion[]>([])
  const [open, setOpen] = useState(false)
  const [active, setActive] = useState(-1)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const boxRef = useRef<HTMLDivElement>(null)

  // Адрес поменяли снаружи (например, кликом по карте) — показываем его в поле
  if (value?.address !== prevAddress) {
    setPrevAddress(value?.address)
    if (value) setText(value.address)
  }

  const enabled = geo?.enabled ?? false
  const query = text.trim()
  const needSearch = enabled && open && query.length >= 3 && query !== value?.address

  useEffect(() => {
    if (!needSearch) return
    let cancelled = false
    const t = setTimeout(async () => {
      setLoading(true)
      try {
        const found = await searchAddress(query)
        if (!cancelled) {
          setItems(found)
          setActive(found.length ? 0 : -1)
          setError(null)
        }
      } catch (e) {
        if (!cancelled) setError((e as Error).message)
      } finally {
        if (!cancelled) setLoading(false)
      }
    }, 350)
    return () => {
      cancelled = true
      clearTimeout(t)
    }
  }, [needSearch, query])

  // Клик мимо списка закрывает его
  useEffect(() => {
    const close = (e: MouseEvent) => {
      if (!boxRef.current?.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', close)
    return () => document.removeEventListener('mousedown', close)
  }, [])

  const pick = (s: GeoSuggestion) => {
    setText(s.address)
    setOpen(false)
    onChange({ address: s.address, token: s.token, lat: s.lat, lon: s.lon })
  }

  const showList = needSearch && (items.length > 0 || (!loading && query.length >= 3))

  return (
    <div ref={boxRef} className="relative">
      <MapPin className="pointer-events-none absolute top-1/2 left-3.5 size-4 -translate-y-1/2 text-steel" aria-hidden />
      <Input
        id={id}
        role={enabled ? 'combobox' : undefined}
        aria-expanded={enabled ? showList : undefined}
        aria-controls={enabled ? listId : undefined}
        aria-autocomplete={enabled ? 'list' : undefined}
        aria-invalid={invalid}
        aria-describedby={describedBy}
        autoComplete="off"
        className="pr-9 pl-10"
        placeholder={placeholder ?? 'Город, улица, дом'}
        value={text}
        onFocus={() => setOpen(true)}
        onChange={(e) => {
          setText(e.target.value)
          setOpen(true)
          // Текст правят руками — выбранный адрес больше не действителен
          if (enabled) onChange(null)
          else onChange(e.target.value.trim() ? { address: e.target.value.trim(), token: null } : null)
        }}
        onKeyDown={(e) => {
          if (!showList) return
          if (e.key === 'ArrowDown') {
            e.preventDefault()
            setActive((i) => Math.min(i + 1, items.length - 1))
          } else if (e.key === 'ArrowUp') {
            e.preventDefault()
            setActive((i) => Math.max(i - 1, 0))
          } else if (e.key === 'Enter' && items[active]) {
            e.preventDefault()
            pick(items[active])
          } else if (e.key === 'Escape') {
            setOpen(false)
          }
        }}
      />
      {loading && (
        <LoaderCircle className="absolute top-1/2 right-3 size-4 -translate-y-1/2 animate-spin text-steel" aria-hidden />
      )}
      {showList && (
        <ul
          id={listId}
          role="listbox"
          className="absolute inset-x-0 top-full z-[1200] mt-1 max-h-72 overflow-auto rounded-md border border-line bg-paper py-1 shadow-lg"
        >
          {items.length === 0 && <li className="px-3.5 py-2 text-sm text-steel">Ничего не нашлось. Уточните адрес</li>}
          {items.map((s, i) => (
            <li
              key={`${s.address}-${s.lat}`}
              role="option"
              aria-selected={i === active}
              onMouseEnter={() => setActive(i)}
              onMouseDown={(e) => {
                e.preventDefault() // не терять фокус поля до выбора
                pick(s)
              }}
              className={cn('cursor-pointer px-3.5 py-2 text-[15px]', i === active && 'bg-signal/20')}
            >
              {s.address}
            </li>
          ))}
        </ul>
      )}
      {error && <p className="mt-1 text-sm text-danger">{error}</p>}
    </div>
  )
}
