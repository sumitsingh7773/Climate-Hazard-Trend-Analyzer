import { useEffect, useRef } from 'react'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'

interface LocationMapProps {
  latitude: number
  longitude: number
  regionName: string
  onLocationSelect?: (lat: number, lon: number) => void
}

export function LocationMap({ latitude, longitude, regionName, onLocationSelect }: LocationMapProps) {
  const mapContainerRef = useRef<HTMLDivElement | null>(null)
  const mapInstanceRef = useRef<L.Map | null>(null)
  const markerRef = useRef<L.Marker | null>(null)

  useEffect(() => {
    if (!mapContainerRef.current) return

    // Initialize Leaflet map
    if (!mapInstanceRef.current) {
      const map = L.map(mapContainerRef.current, {
        center: [latitude, longitude],
        zoom: 7,
        zoomControl: true,
        attributionControl: false,
      })

      // Sleek dark Carto tile layer
      L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png', {
        maxZoom: 19,
        subdomains: 'abcd',
      }).addTo(map)

      // Click to select custom coordinates
      map.on('click', (e: L.LeafletMouseEvent) => {
        if (onLocationSelect) {
          const lat = parseFloat(e.latlng.lat.toFixed(4))
          const lon = parseFloat(e.latlng.lng.toFixed(4))
          onLocationSelect(lat, lon)
        }
      })

      mapInstanceRef.current = map
    }

    const map = mapInstanceRef.current

    // Pulsing custom pin
    const pinIcon = L.divIcon({
      className: 'custom-map-pin',
      html: `
        <div class="pin-ring"></div>
        <div class="pin-dot"></div>
      `,
      iconSize: [28, 28],
      iconAnchor: [14, 14],
    })

    if (!markerRef.current) {
      markerRef.current = L.marker([latitude, longitude], { icon: pinIcon })
        .addTo(map)
        .bindPopup(`<strong>${regionName}</strong><br/>${latitude.toFixed(4)}°, ${longitude.toFixed(4)}°`)
    } else {
      markerRef.current.setLatLng([latitude, longitude])
      markerRef.current.setPopupContent(`<strong>${regionName}</strong><br/>${latitude.toFixed(4)}°, ${longitude.toFixed(4)}°`)
    }

    map.setView([latitude, longitude], map.getZoom() || 7, { animate: true })

    // Invalidate size after mount / resize
    const timer = setTimeout(() => {
      map.invalidateSize()
    }, 200)

    return () => {
      clearTimeout(timer)
      if (mapInstanceRef.current) {
        mapInstanceRef.current.remove()
        mapInstanceRef.current = null
        markerRef.current = null
      }
    }
  }, [latitude, longitude, regionName, onLocationSelect])

  return (
    <div className="map-wrapper">
      <div className="map-toolbar">
        <span className="map-coords-badge">
          📍 {latitude.toFixed(4)}° N, {longitude.toFixed(4)}° E
        </span>
        <span className="map-hint">Click anywhere on map to reposition coordinates</span>
      </div>
      <div ref={mapContainerRef} className="leaflet-map-container" />
    </div>
  )
}
