import L from 'leaflet'
import { useEffect } from 'react'
import { MapContainer, Marker, TileLayer, useMap, useMapEvents } from 'react-leaflet'
import { DEFAULT_CENTER, DEFAULT_ZOOM, TILE_ATTRIBUTION, TILE_URL } from './constants'

const pinIcon = L.divIcon({
  className: 'price-pin-anchor',
  iconSize: [0, 0],
  html: '<span class="price-pin is-active">Техника здесь</span>',
})

type Point = { lat: number; lng: number }

function ClickHandler({ onChange }: { onChange: (p: Point) => void }) {
  useMapEvents({ click: (e) => onChange({ lat: e.latlng.lat, lng: e.latlng.lng }) })
  return null
}

function CenterOnce({ value }: { value: Point | null }) {
  const map = useMap()
  useEffect(() => {
    if (value) map.setView([value.lat, value.lng], Math.max(map.getZoom(), 13))
    // Центрируем только при первом показе, чтобы карта не прыгала за каждым кликом
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [map])
  return null
}

/** Владелец отмечает, где стоит техника: клик по карте или перетаскивание метки */
export function LocationPicker({
  value,
  onChange,
  invalid,
}: {
  value: Point | null
  onChange: (p: Point) => void
  invalid?: boolean
}) {
  return (
    <div
      className={
        'h-72 overflow-hidden rounded-md border ' + (invalid ? 'border-danger' : 'border-line')
      }
    >
      <MapContainer center={DEFAULT_CENTER} zoom={DEFAULT_ZOOM} className="size-full">
        <TileLayer url={TILE_URL} attribution={TILE_ATTRIBUTION} />
        <ClickHandler onChange={onChange} />
        <CenterOnce value={value} />
        {value && (
          <Marker
            position={[value.lat, value.lng]}
            icon={pinIcon}
            draggable
            eventHandlers={{
              dragend: (e) => {
                const ll = (e.target as L.Marker).getLatLng()
                onChange({ lat: ll.lat, lng: ll.lng })
              },
            }}
          />
        )}
      </MapContainer>
    </div>
  )
}
