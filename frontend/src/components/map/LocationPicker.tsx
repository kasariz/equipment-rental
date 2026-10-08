import type { YMap } from '@yandex/ymaps3-types'
import { useEffect, useRef, useState } from 'react'
import { cn } from '@/lib/utils'
import { boundsContain, DEFAULT_CENTER, DEFAULT_ZOOM, toLngLat, type YMapsComponents } from '@/lib/ymaps'
import { MapFrame, ZoomButtons } from './MapFrame'

type Point = { lat: number; lng: number }
type Props = { value: Point | null; onChange: (p: Point) => void; invalid?: boolean }

function Picker({ y, value, onChange }: Props & { y: YMapsComponents }) {
  const { YMap, YMapDefaultSchemeLayer, YMapDefaultFeaturesLayer, YMapMarker, YMapListener } = y
  const mapRef = useRef<YMap>(null)
  // Стартовая позиция: на метке, если она уже есть. Дальше карта не прыгает за каждым кликом
  const [initial] = useState(() =>
    value ? { center: toLngLat(value.lat, value.lng), zoom: 14 } : { center: DEFAULT_CENTER, zoom: DEFAULT_ZOOM },
  )

  // Точку поменяли снаружи (выбрали адрес из подсказок) и она за краем карты — показываем её.
  // Клик по карте всегда внутри видимой области, поэтому от кликов карта не прыгает
  useEffect(() => {
    const map = mapRef.current
    if (!map || !value) return
    const point = toLngLat(value.lat, value.lng)
    if (!boundsContain(map.bounds, point)) map.setLocation({ center: point, zoom: Math.max(map.zoom, 14), duration: 300 })
  }, [value])

  return (
    <div className="relative size-full">
      {/* Контейнер карты всегда на всю площадь родителя */}
      <div className="absolute inset-0 [&>div]:size-full">
        <YMap ref={mapRef} location={initial}>
          <YMapDefaultSchemeLayer />
          <YMapDefaultFeaturesLayer />
          <YMapListener
            layer="any"
            onClick={(_object, event) => onChange({ lat: event.coordinates[1], lng: event.coordinates[0] })}
          />
          {value && (
            <YMapMarker
              coordinates={toLngLat(value.lat, value.lng)}
              draggable
              mapFollowsOnDrag
              onDragEnd={(coords) => onChange({ lat: coords[1], lng: coords[0] })}
            >
              <span className="price-pin is-active cursor-grab">Техника здесь</span>
            </YMapMarker>
          )}
        </YMap>
      </div>
      <ZoomButtons mapRef={mapRef} />
    </div>
  )
}

/** Владелец отмечает, где стоит техника: клик по карте или перетаскивание метки */
export function LocationPicker(props: Props) {
  return (
    <div className={cn('h-72 overflow-hidden rounded-md border', props.invalid ? 'border-danger' : 'border-line')}>
      <MapFrame>{(y) => <Picker y={y} {...props} />}</MapFrame>
    </div>
  )
}
