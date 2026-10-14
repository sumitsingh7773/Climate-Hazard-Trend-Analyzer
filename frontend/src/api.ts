import type { Analysis, HazardType, Region } from './types'

const API_BASE = (import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000').replace(/\/$/, '')

export async function getRegions(): Promise<Region[]> {
  const response = await fetch(`${API_BASE}/api/regions`)
  if (!response.ok) throw new Error('Could not load region presets')
  const data = await response.json()
  return data.regions
}

export async function getAnalysis(params: {
  hazard: HazardType
  latitude: number
  longitude: number
  start_date: string
  end_date: string
}): Promise<Analysis> {
  const query = new URLSearchParams({
    latitude: String(params.latitude),
    longitude: String(params.longitude),
    start_date: params.start_date,
    end_date: params.end_date,
  })
  const response = await fetch(`${API_BASE}/api/analysis/${params.hazard}?${query}`)
  const data = await response.json()
  if (!response.ok) {
    throw new Error(data.detail || 'Analysis request failed')
  }
  return data as Analysis
}

export async function checkApiHealth(): Promise<{ status: string; database: string }> {
  try {
    const res = await fetch(`${API_BASE}/api/health`)
    if (!res.ok) return { status: 'degraded', database: 'unknown' }
    return await res.json()
  } catch {
    return { status: 'offline', database: 'unavailable' }
  }
}
