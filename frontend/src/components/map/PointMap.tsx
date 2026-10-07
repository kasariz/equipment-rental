import type { YMap } from '@yandex/ymaps3-types'
import { useRef, useState } from 'react'
import { toLngLat, type YMapsComponents } from '@/lib/ymaps'
import { MapFrame, ZoomButtons } from './MapFrame'

type Props = { lat: number; lng: number; label: string }

function Point({ y, lat, lng, label }: Props & { y: YMapsComponents }) {
  const { YMap, YMapDefaultSchemeLayer, YMapDefaultFeaturesLayer, YMapMarker } = y
  const mapRef = useRef<YMap>(null)
  const [location] = useState(() => ({ center: toLngLat(lat, lng), zoom: 13 }))
  return (
    <div className="relative size-full">
      {/* Без scrollZoom: страница должна прокручиваться колесом, а не застревать на карте */}
      {/* Контейнер карты всегда на всю площадь родителя */}
      <div className="absolute inset-0 [&>div]:size-full">
        <YMap ref={mapRef} location={location} behaviors={['drag', 'pinchZoom', 'dblClick']}>
          <YMapDefaultSchemeLayer />
          <YMapDefaultFeaturesLayer />
          <YMapMarker coordinates={toLngLat(lat, lng)}>
            <span className="price-pin is-active">{label}</span>
          </YMapMarker>
        </YMap>
      </div>
      <ZoomButtons mapRef={mapRef} />
    </div>
  )
}

/** Небольшая карта с одной точкой: где стоит техника */
export function PointMap(props: Props) {
  return <MapFrame>{(y) => <Point y={y} {...props} />}</MapFrame>
}
