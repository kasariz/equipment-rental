import L from 'leaflet'
import { useEffect, useMemo, useRef } from 'react'
import { MapContainer, Marker, TileLayer, useMap } from 'react-leaflet'
import type { EquipmentListItem } from '@/api/client'
import { formatRub } from '@/lib/format'
import { DEFAULT_CENTER, DEFAULT_ZOOM, TILE_ATTRIBUTION, TILE_URL } from './constants'

function priceIcon(price: number, active: boolean) {
  return L.divIcon({
    className: 'price-pin-anchor',
    iconSize: [0, 0],
    html: `<span class="price-pin${active ? ' is-active' : ''}">${formatRub(price)}</span>`,
  })
}

const userIcon = L.divIcon({
  className: 'price-pin-anchor',
  iconSize: [16, 16],
  iconAnchor: [8, 8],
  html: '<div class="user-dot"></div>',
})

/** Подгоняет карту под найденную технику, но только когда меняется сам набор результатов */
function FitToItems({ items, userPoint }: { items: EquipmentListItem[]; userPoint?: [number, number] }) {
  const map = useMap()
  const key = items.map((i) => i.id).join(',') + (userPoint?.join(',') ?? '')
  const lastKey = useRef<string | null>(null)

  useEffect(() => {
    if (key === lastKey.current) return
    lastKey.current = key
    const points: L.LatLngTuple[] = items.map((i) => [i.latitude, i.longitude])
    if (userPoint) points.push(userPoint)
    if (points.length === 0) return
    if (points.length === 1) map.setView(points[0], 13)
    else map.fitBounds(points, { padding: [48, 48], maxZoom: 14 })
  }, [key, items, userPoint, map])

  return null
}

/** Плавно показывает выбранную в списке технику, если она за краем карты */
function PanToSelected({ item }: { item?: EquipmentListItem }) {
  const map = useMap()
  useEffect(() => {
    if (!item) return
    const point = L.latLng(item.latitude, item.longitude)
    if (!map.getBounds().pad(-0.1).contains(point)) map.panTo(point)
  }, [item, map])
  return null
}

type Props = {
  items: EquipmentListItem[]
  selectedId: number | null
  onSelect: (id: number) => void
  userPoint?: [number, number]
}

export function EquipmentMap({ items, selectedId, onSelect, userPoint }: Props) {
  const selected = useMemo(() => items.find((i) => i.id === selectedId), [items, selectedId])

  return (
    <MapContainer center={DEFAULT_CENTER} zoom={DEFAULT_ZOOM} className="size-full" zoomControl={false}>
      <TileLayer url={TILE_URL} attribution={TILE_ATTRIBUTION} />
      <FitToItems items={items} userPoint={userPoint} />
      <PanToSelected item={selected} />
      {userPoint && <Marker position={userPoint} icon={userIcon} interactive={false} />}
      {items.map((item) => {
        const active = item.id === selectedId
        return (
          <Marker
            key={item.id}
            position={[item.latitude, item.longitude]}
            icon={priceIcon(item.price_per_hour, active)}
            zIndexOffset={active ? 1000 : 0}
            title={item.name}
            eventHandlers={{ click: () => onSelect(item.id) }}
          />
        )
      })}
    </MapContainer>
  )
}
