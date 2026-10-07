import 'leaflet/dist/leaflet.css'
import type { LatLngTuple } from 'leaflet'

export const DEFAULT_CENTER: LatLngTuple = [47.2357, 39.7015] // Ростов-на-Дону
export const DEFAULT_ZOOM = 11

export const TILE_URL = 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png'
export const TILE_ATTRIBUTION =
  '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
