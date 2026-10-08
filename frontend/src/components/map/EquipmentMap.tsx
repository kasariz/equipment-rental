import type { YMap } from '@yandex/ymaps3-types'
import { useEffect, useRef, useState } from 'react'
import type { EquipmentListItem } from '@/api/client'
import { formatRub } from '@/lib/format'
import {
  boundsContain,
  boundsFor,
  DEFAULT_CENTER,
  DEFAULT_ZOOM,
  toLngLat,
  type YMapsComponents,
} from '@/lib/ymaps'
import { MapFrame, ZoomButtons } from './MapFrame'

type Props = {
  items: EquipmentListItem[]
  selectedId: number | null
  onSelect: (id: number) => void
  userPoint?: [number, number] // [широта, долгота]
  // Поиск в видимой области: карта не подгоняется под результаты, а после сдвига появляется кнопка
  areaActive?: boolean
  onSearchArea?: (area: [number, number, number, number]) => void
}

type Location = Parameters<YMap['setLocation']>[0]

function locationFor(items: EquipmentListItem[], userPoint?: [number, number]): Location {
  const points = items.map((i) => toLngLat(i.latitude, i.longitude))
  if (userPoint) points.push(toLngLat(userPoint[0], userPoint[1]))
  if (points.length === 0) return { center: DEFAULT_CENTER, zoom: DEFAULT_ZOOM }
  if (points.length === 1) return { center: points[0], zoom: 13, duration: 300 }
  return { bounds: boundsFor(points), duration: 300 }
}

function Map({ y, items, selectedId, onSelect, userPoint, areaActive, onSearchArea }: Props & { y: YMapsComponents }) {
  const { YMap, YMapDefaultSchemeLayer, YMapDefaultFeaturesLayer, YMapMarker, YMapListener } = y
  const [moved, setMoved] = useState(false)
  const mapRef = useRef<YMap>(null)

  // Подгоняем карту под результаты, только когда меняется сам набор техники.
  // Если человек сам подвинул карту, перерисовки её не дёргают
  const fitKey = items.map((i) => i.id).join(',') + (userPoint?.join(',') ?? '')
  const [fit, setFit] = useState(() => ({ key: fitKey, location: locationFor(items, userPoint) }))
  if (fit.key !== fitKey) {
    // В режиме «искать здесь» карта остаётся там, где её поставил человек
    setFit({ key: fitKey, location: areaActive ? fit.location : locationFor(items, userPoint) })
  }

  // Выбранная в списке техника за краем карты — плавно показываем её
  const selected = items.find((i) => i.id === selectedId)
  useEffect(() => {
    const map = mapRef.current
    if (!map || !selected) return
    const point = toLngLat(selected.latitude, selected.longitude)
    if (!boundsContain(map.bounds, point)) map.setLocation({ center: point, duration: 300 })
  }, [selected])

  return (
    <div className="relative size-full">
      {/* Контейнер карты всегда на всю площадь родителя */}
      <div className="absolute inset-0 [&>div]:size-full">
        <YMap ref={mapRef} location={fit.location}>
          <YMapDefaultSchemeLayer />
          <YMapDefaultFeaturesLayer />
          {/* onActionEnd срабатывает только на действия человека: перетаскивание и масштаб */}
          {onSearchArea && <YMapListener onActionEnd={() => setMoved(true)} />}
          {userPoint && (
            <YMapMarker coordinates={toLngLat(userPoint[0], userPoint[1])}>
              <div className="user-dot" aria-label="Вы здесь" />
            </YMapMarker>
          )}
          {items.map((item) => {
            const active = item.id === selectedId
            return (
              <YMapMarker
                key={item.id}
                coordinates={toLngLat(item.latitude, item.longitude)}
                zIndex={active ? 1000 : 0}
                onClick={() => onSelect(item.id)}
              >
                <span className={active ? 'price-pin is-active' : 'price-pin'} title={item.name}>
                  {formatRub(item.price_per_hour)}
                </span>
              </YMapMarker>
            )
          })}
        </YMap>
      </div>
      <ZoomButtons mapRef={mapRef} />
      {onSearchArea && moved && (
        <button
          type="button"
          onClick={() => {
            const map = mapRef.current
            if (!map) return
            const [[left, top], [right, bottom]] = map.bounds
            onSearchArea([bottom, top, left, right])
            setMoved(false)
          }}
          className="absolute top-3 left-1/2 z-10 -translate-x-1/2 rounded-full bg-ink px-4 py-2 text-sm font-medium text-paper shadow-lg hover:bg-ink/85"
        >
          Искать в этой области
        </button>
      )}
    </div>
  )
}

export function EquipmentMap(props: Props) {
  return <MapFrame>{(y) => <Map y={y} {...props} />}</MapFrame>
}
