import { useEffect, useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import {
  Area,
  Bar,
  CartesianGrid,
  ComposedChart,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import {
  Activity,
  AlertTriangle,
  CalendarDays,
  CloudRain,
  Compass,
  Download,
  Flame,
  Globe2,
  Info,
  MapPin,
  Printer,
  RefreshCw,
  Sun,
  ThermometerSun,
  TrendingDown,
  TrendingUp,
} from 'lucide-react'
import { checkApiHealth, getAnalysis, getRegions } from './api'
import { LocationMap } from './components/LocationMap'
import type { Analysis, HazardType, Region } from './types'

const CURRENT_YEAR = new Date().getFullYear()

function App() {
  const [regions, setRegions] = useState<Region[]>([])
  const [selectedRegionIndex, setSelectedRegionIndex] = useState('0')
  const [isCustomCoords, setIsCustomCoords] = useState(false)
  const [customLat, setCustomLat] = useState('25.5941')
  const [customLon, setCustomLon] = useState('85.1376')
  const [showMap, setShowMap] = useState(true)

  const [hazard, setHazard] = useState<HazardType>('heatwave')
  const [startYear, setStartYear] = useState('1990')
  const [endYear, setEndYear] = useState('2020')

  const [analysis, setAnalysis] = useState<Analysis | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [eventSearch, setEventSearch] = useState('')
  const [apiHealth, setApiHealth] = useState<{ status: string; database: string }>({
    status: 'checking',
    database: 'unknown',
  })

  // Load regions and API health on mount
  useEffect(() => {
    getRegions()
      .then(setRegions)
      .catch(() => {
        setRegions([
          { name: 'Patna, India', latitude: 25.5941, longitude: 85.1376 },
          { name: 'Delhi, India', latitude: 28.6139, longitude: 77.209 },
          { name: 'Mumbai, India', latitude: 19.076, longitude: 72.8777 },
          { name: 'Kolkata, India', latitude: 22.5726, longitude: 88.3639 },
          { name: 'Ranchi, India', latitude: 23.3441, longitude: 85.3096 },
          { name: 'Bengaluru, India', latitude: 12.9716, longitude: 77.5946 },
          { name: 'Chennai, India', latitude: 13.0827, longitude: 80.2707 },
          { name: 'London, UK', latitude: 51.5074, longitude: -0.1278 },
        ])
      })

    checkApiHealth().then(setApiHealth)
  }, [])

  // Derive current coordinates & location name
  const currentRegion = regions[Number(selectedRegionIndex)]
  const activeLat = isCustomCoords ? parseFloat(customLat) || 0 : currentRegion?.latitude || 25.5941
  const activeLon = isCustomCoords ? parseFloat(customLon) || 0 : currentRegion?.longitude || 85.1376
  const activeLocationName = isCustomCoords
    ? `Custom Location (${activeLat.toFixed(2)}°, ${activeLon.toFixed(2)}°)`
    : currentRegion?.name || 'Selected Region'

  function handleMapLocationSelect(lat: number, lon: number) {
    setIsCustomCoords(true)
    setCustomLat(String(lat))
    setCustomLon(String(lon))
  }

  function handleUseMyLocation() {
    if (!navigator.geolocation) {
      setError('Geolocation is not supported by your browser.')
      return
    }
    navigator.geolocation.getCurrentPosition(
      pos => {
        setIsCustomCoords(true)
        setCustomLat(pos.coords.latitude.toFixed(4))
        setCustomLon(pos.coords.longitude.toFixed(4))
      },
      () => setError('Could not retrieve current location.')
    )
  }

  async function runAnalysis() {
    const start = Number(startYear)
    const end = Number(endYear)
    if (!Number.isInteger(start) || !Number.isInteger(end) || start < 1940 || end > CURRENT_YEAR - 1 || start >= end) {
      setError(`Choose valid years between 1940 and ${CURRENT_YEAR - 1}; start must be before end.`)
      return
    }

    if (activeLat < -90 || activeLat > 90 || activeLon < -180 || activeLon > 180) {
      setError('Latitude must be between -90 and 90; longitude between -180 and 180.')
      return
    }

    setLoading(true)
    setError('')
    try {
      const result = await getAnalysis({
        hazard,
        latitude: activeLat,
        longitude: activeLon,
        start_date: `${start}-01-01`,
        end_date: `${end}-12-31`,
      })
      setAnalysis(result)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Unexpected error executing climate analysis.')
    } finally {
      setLoading(false)
    }
  }

  function exportCsv() {
    if (!analysis) return
    const yearlyRows = [
      ['YEARLY AGGREGATES'],
      ['year', 'events', 'hazard_days', 'mean_duration_days', 'peak_intensity', 'rolling_avg_3yr', 'trend_fit'],
      ...analysis.yearlyStats.map(r => [
        r.year,
        r.events,
        r.hazardDays ?? r.heatwaveDays ?? 0,
        r.meanEventDurationDays ?? 0,
        r.peakIntensity ?? 0,
        r.rollingAvgEvents3Yr ?? 0,
        r.trendLineEvents ?? 0,
      ]),
      [],
      ['DETECTED EVENTS CATALOG'],
      ['start_date', 'end_date', 'duration_days', 'peak_value', 'mean_excess_or_total'],
      ...analysis.events.map(e => [
        e.startDate,
        e.endDate,
        e.durationDays,
        e.maxTemperatureC ?? e.peakPrecipitationMm ?? 0,
        e.meanExcessAboveThresholdC ?? e.totalPrecipitationMm ?? 0,
      ]),
    ]

    const csvContent = yearlyRows.map(row => row.join(',')).join('\n')
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `${analysis.hazard}-analysis-${startYear}-${endYear}.csv`
    link.click()
    URL.revokeObjectURL(url)
  }

  function handlePrintReport() {
    window.print()
  }

  const filteredEvents = useMemo(() => {
    if (!analysis) return []
    if (!eventSearch.trim()) return analysis.events
    const q = eventSearch.toLowerCase()
    return analysis.events.filter(e => e.startDate.includes(q) || e.endDate.includes(q))
  }, [analysis, eventSearch])

  const chartData = useMemo(() => analysis?.yearlyStats ?? [], [analysis])

  const hazardAccent =
    hazard === 'heatwave' ? 'active-heatwave' : hazard === 'rainfall' ? 'active-rainfall' : 'active-drought'

  return (
    <div className={`app-shell hazard-theme-${hazard}`}>
      {/* AMBIENT CLIMATE BACKDROP */}
      <div className={`hazard-ambient-backdrop ambient-${hazard}`} aria-hidden="true">
        <div className="ambient-glow" />
        <div className="ambient-particles" />
      </div>

      {/* TOPBAR */}
      <header className="topbar">
        <a className="brand" href="#">
          <span className="brand-icon">
            <Activity size={22} />
          </span>
          <span>
            CLIMATE <span className="brand-light">/ HAZARD ANALYZER</span>
          </span>
        </a>

        <div className="topbar-actions">
          <span className="status-pill">
            <span
              className={`status-dot ${
                apiHealth.status === 'healthy'
                  ? apiHealth.database === 'connected'
                    ? 'online'
                    : 'fallback'
                  : 'offline'
              }`}
            />
            {apiHealth.status === 'healthy'
              ? apiHealth.database === 'connected'
                ? 'MongoDB Connected'
                : 'In-Memory Cache'
              : 'API Offline'}
          </span>

          {analysis && (
            <>
              <button className="secondary-button" onClick={exportCsv} title="Export CSV Data">
                <Download size={14} /> CSV
              </button>
              <button className="secondary-button" onClick={handlePrintReport} title="Print or Save PDF">
                <Printer size={14} /> PDF Report
              </button>
            </>
          )}
        </div>
      </header>

      <main className="page">
        {/* HERO */}
        <section className="hero">
          <div className="eyebrow">
            <span className="eyebrow-line" /> CLIMATE HAZARD TREND ANALYZER
          </div>
          <h1>
            Evidence-Based Climate Hazards.<br />
            <span>Track Long-Term Shifts.</span>
          </h1>
          <p>
            Perform empirical multi-hazard climate risk analysis using verified Open-Meteo reanalysis archives. Detect
            percentile-based extremes, moving averages, and decadal trends with full methodology transparency.
          </p>
        </section>

        {/* HAZARD SELECTOR TABS */}
        <div className="hazard-selector-bar">
          <button
            className={`hazard-tab ${hazard === 'heatwave' ? 'active-heatwave' : ''}`}
            onClick={() => setHazard('heatwave')}
          >
            <Flame size={15} /> HEATWAVES
          </button>
          <button
            className={`hazard-tab ${hazard === 'rainfall' ? 'active-rainfall' : ''}`}
            onClick={() => setHazard('rainfall')}
          >
            <CloudRain size={15} /> EXTREME RAINFALL
          </button>
          <button
            className={`hazard-tab ${hazard === 'drought' ? 'active-drought' : ''}`}
            onClick={() => setHazard('drought')}
          >
            <Sun size={15} /> DROUGHT SPELLS
          </button>
        </div>

        {/* FILTERS PANEL */}
        <section className="filters panel">
          <div className="filter-header">
            <div>
              <span className="section-kicker">01 / CONFIGURE PARAMETERS</span>
              <h2>Configure Hazard &amp; Geography</h2>
            </div>

            <div className="mode-toggle">
              <span>Location Mode:</span>
              <button
                className={!isCustomCoords ? 'active' : ''}
                onClick={() => setIsCustomCoords(false)}
              >
                Presets
              </button>
              <button
                className={isCustomCoords ? 'active' : ''}
                onClick={() => setIsCustomCoords(true)}
              >
                Custom Lat/Lon
              </button>
            </div>
          </div>

          <div className={`filter-grid ${isCustomCoords ? 'custom-mode' : ''}`}>
            {!isCustomCoords ? (
              <label>
                <span>
                  <MapPin size={14} /> REGION PRESET
                </span>
                <select
                  value={selectedRegionIndex}
                  onChange={e => {
                    const idx = e.target.value
                    setSelectedRegionIndex(idx)
                    const reg = regions[Number(idx)]
                    if (reg) {
                      setCustomLat(String(reg.latitude))
                      setCustomLon(String(reg.longitude))
                    }
                  }}
                >
                  {regions.map((r, i) => (
                    <option value={i} key={`${r.name}-${i}`}>
                      {r.name} ({r.latitude.toFixed(2)}°, {r.longitude.toFixed(2)}°)
                    </option>
                  ))}
                </select>
              </label>
            ) : (
              <>
                <label>
                  <span>
                    <Compass size={14} /> LATITUDE (°N)
                  </span>
                  <input
                    type="number"
                    step="0.0001"
                    min="-90"
                    max="90"
                    value={customLat}
                    onChange={e => setCustomLat(e.target.value)}
                    placeholder="e.g. 25.5941"
                  />
                </label>
                <label>
                  <span>
                    <Compass size={14} /> LONGITUDE (°E)
                  </span>
                  <input
                    type="number"
                    step="0.0001"
                    min="-180"
                    max="180"
                    value={customLon}
                    onChange={e => setCustomLon(e.target.value)}
                    placeholder="e.g. 85.1376"
                  />
                </label>
              </>
            )}

            <label>
              <span>
                <CalendarDays size={14} /> FROM YEAR
              </span>
              <input
                type="number"
                min="1940"
                max={CURRENT_YEAR - 1}
                value={startYear}
                onChange={e => setStartYear(e.target.value)}
              />
            </label>

            <label>
              <span>
                <CalendarDays size={14} /> TO YEAR
              </span>
              <input
                type="number"
                min="1941"
                max={CURRENT_YEAR - 1}
                value={endYear}
                onChange={e => setEndYear(e.target.value)}
              />
            </label>

            <button
              className="primary-button"
              onClick={runAnalysis}
              disabled={loading}
            >
              {loading ? (
                <>
                  <RefreshCw className="spin" size={16} /> ANALYZING
                </>
              ) : (
                <>
                  <Activity size={16} /> ANALYZE TRENDS
                </>
              )}
            </button>
          </div>

          <div className="quick-years">
            <span style={{ fontSize: 11, color: '#627791', alignSelf: 'center', fontFamily: 'DM Mono' }}>
              Quick Ranges:
            </span>
            <button className="quick-chip" onClick={() => { setStartYear('1990'); setEndYear('2020'); }}>
              1990–2020 (30 Yrs)
            </button>
            <button className="quick-chip" onClick={() => { setStartYear('2000'); setEndYear('2023'); }}>
              2000–2023
            </button>
            <button className="quick-chip" onClick={() => { setStartYear(String(CURRENT_YEAR - 20)); setEndYear(String(CURRENT_YEAR - 1)); }}>
              Past 20 Yrs
            </button>
            <button className="quick-chip" onClick={() => { setStartYear(String(CURRENT_YEAR - 10)); setEndYear(String(CURRENT_YEAR - 1)); }}>
              Past 10 Yrs
            </button>
            {isCustomCoords && (
              <button className="quick-chip" onClick={handleUseMyLocation} style={{ color: '#4fe0c2' }}>
                📍 My Current Location
              </button>
            )}
          </div>

          <button className="map-toggle-btn" onClick={() => setShowMap(!showMap)}>
            <Globe2 size={13} /> {showMap ? 'Hide Location Map' : 'Show Interactive Location Map'}
          </button>

          {showMap && (
            <LocationMap
              latitude={activeLat}
              longitude={activeLon}
              regionName={activeLocationName}
              onLocationSelect={handleMapLocationSelect}
            />
          )}
        </section>

        {/* ERROR NOTIFICATION */}
        {error && (
          <div className="error-banner" role="alert">
            <AlertTriangle size={18} />
            <div>
              <strong>Analysis Error:</strong> {error}
            </div>
          </div>
        )}

        {/* EMPTY STATE */}
        {!analysis && !loading && (
          <section className="empty-state panel">
            <div className="empty-icon">
              {hazard === 'heatwave' ? (
                <ThermometerSun size={28} />
              ) : hazard === 'rainfall' ? (
                <CloudRain size={28} />
              ) : (
                <Sun size={28} />
              )}
            </div>
            <h2>Ready to investigate climate trends</h2>
            <p>
              Choose your hazard type, geographical point, and chronological window above, then press{' '}
              <strong>Analyze Trends</strong> to evaluate historical observations directly from Open-Meteo.
            </p>
          </section>
        )}

        {/* LOADING STATE */}
        {loading && (
          <section className="empty-state panel">
            <div className="loader" />
            <h2>Evaluating Historical Climate Archive…</h2>
            <p>
              Querying high-resolution observations, validating daily series continuity, calculating regional
              percentile thresholds, and fitting linear regression trends.
            </p>
          </section>
        )}

        {/* RESULTS SECTION */}
        {analysis && !loading && (
          <>
            <section className="results-heading">
              <div>
                <span className="section-kicker">02 / EMPIRICAL FINDINGS</span>
                <h2>
                  {activeLocationName}{' '}
                  <span>
                    · {analysis.period?.startDate.slice(0, 4)}–{analysis.period?.endDate.slice(0, 4)} ({analysis.hazardName || analysis.hazard})
                  </span>
                </h2>
              </div>
              <div className="results-actions">
                <button className="secondary-button" onClick={exportCsv}>
                  <Download size={14} /> Export CSV
                </button>
                <button className="secondary-button" onClick={handlePrintReport}>
                  <Printer size={14} /> Print PDF
                </button>
              </div>
            </section>

            {/* METRICS GRID */}
            <section className="metrics-grid">
              <Metric
                icon={
                  hazard === 'heatwave' ? (
                    <Flame size={18} />
                  ) : hazard === 'rainfall' ? (
                    <CloudRain size={18} />
                  ) : (
                    <Sun size={18} />
                  )
                }
                label="TOTAL HAZARD EVENTS"
                value={String(analysis.totalEvents)}
                detail="Qualifying events detected"
              />

              <Metric
                icon={<CalendarDays size={18} />}
                label="TOTAL HAZARD DAYS"
                value={String(analysis.totalHazardDays ?? analysis.totalHeatwaveDays ?? 0)}
                detail="Cumulative days in hazard runs"
              />

              <Metric
                icon={<ThermometerSun size={18} />}
                label="REGIONAL THRESHOLD"
                value={
                  analysis.threshold == null
                    ? '—'
                    : `${analysis.threshold} ${analysis.thresholdUnit || '°C'}`
                }
                detail={
                  hazard === 'heatwave'
                    ? '95th Percentile Daily Max Temp'
                    : hazard === 'rainfall'
                    ? '95th Percentile Wet-Day Rainfall'
                    : 'Minimum Consecutive Dry Days'
                }
              />

              <Metric
                icon={
                  (analysis.regression?.slope ?? 0) > 0 ? (
                    <TrendingUp size={18} />
                  ) : (
                    <TrendingDown size={18} />
                  )
                }
                label="TREND SLOPE"
                value={
                  analysis.trendSlopeEventsPerYear == null
                    ? '—'
                    : `${analysis.trendSlopeEventsPerYear > 0 ? '+' : ''}${analysis.trendSlopeEventsPerYear.toFixed(
                        3
                      )}/yr`
                }
                detail={
                  analysis.regression ? (
                    <span
                      className={`trend-badge ${
                        analysis.regression.direction === 'increasing'
                          ? 'increasing'
                          : analysis.regression.direction === 'decreasing'
                          ? 'decreasing'
                          : 'stable'
                      }`}
                    >
                      {analysis.regression.direction.toUpperCase()} ({analysis.regression.slope_per_decade > 0 ? '+' : ''}
                      {analysis.regression.slope_per_decade}/decade, R²={analysis.regression.r_squared})
                    </span>
                  ) : (
                    'Ordinary least squares fit'
                  )
                }
              />
            </section>

            {analysis.dataQuality.warning && (
              <div className="warning-banner">
                <AlertTriangle size={16} />
                <span>{analysis.dataQuality.warning}</span>
              </div>
            )}

            {/* CHARTS GRID */}
            <section className="chart-grid">
              {/* CHART 1: Frequency, 3-Yr Rolling Avg, Linear Fit */}
              <div className="panel chart-panel">
                <div className="chart-heading">
                  <div>
                    <span className="section-kicker">ANNUAL FREQUENCY &amp; TREND</span>
                    <h3>Hazard Events per Year</h3>
                  </div>
                  <span className="chart-unit">EVENTS / YEAR</span>
                </div>

                <div className="chart-wrap">
                  <ResponsiveContainer width="100%" height="100%">
                    <ComposedChart data={chartData}>
                      <defs>
                        <linearGradient id="barGrad" x1="0" y1="0" x2="0" y2="1">
                          <stop
                            offset="0%"
                            stopColor={
                              hazard === 'heatwave'
                                ? '#ff7e54'
                                : hazard === 'rainfall'
                                ? '#38bdf8'
                                : '#fbbf24'
                            }
                            stopOpacity={0.8}
                          />
                          <stop
                            offset="100%"
                            stopColor={
                              hazard === 'heatwave'
                                ? '#ff7e54'
                                : hazard === 'rainfall'
                                ? '#38bdf8'
                                : '#fbbf24'
                            }
                            stopOpacity={0.2}
                          />
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 5" stroke="#1d2e44" vertical={false} />
                      <XAxis
                        dataKey="year"
                        tick={{ fill: '#8ea5be', fontSize: 11 }}
                        tickLine={false}
                        axisLine={false}
                        minTickGap={24}
                      />
                      <YAxis
                        tick={{ fill: '#8ea5be', fontSize: 11 }}
                        tickLine={false}
                        axisLine={false}
                        allowDecimals={false}
                      />
                      <Tooltip
                        contentStyle={{
                          background: '#0d1827',
                          border: '1px solid #233954',
                          borderRadius: 10,
                          color: '#e7edf5',
                        }}
                      />
                      <Bar dataKey="events" name="Annual Events" fill="url(#barGrad)" radius={[4, 4, 0, 0]} />
                      <Line
                        type="monotone"
                        dataKey="rollingAvgEvents3Yr"
                        name="3-Yr Rolling Average"
                        stroke="#4fe0c2"
                        strokeWidth={2.4}
                        dot={false}
                      />
                      <Line
                        type="monotone"
                        dataKey="trendLineEvents"
                        name="Linear Trend Fit"
                        stroke="#c084fc"
                        strokeWidth={2}
                        strokeDasharray="4 4"
                        dot={false}
                      />
                    </ComposedChart>
                  </ResponsiveContainer>
                </div>

                <div className="chart-legend-box">
                  <span className="legend-item">
                    <span
                      className="legend-swatch"
                      style={{
                        background:
                          hazard === 'heatwave' ? '#ff7e54' : hazard === 'rainfall' ? '#38bdf8' : '#fbbf24',
                      }}
                    />{' '}
                    Annual Events
                  </span>
                  <span className="legend-item">
                    <span className="legend-swatch" style={{ background: '#4fe0c2' }} /> 3-Yr Rolling Avg
                  </span>
                  <span className="legend-item">
                    <span className="legend-swatch" style={{ background: '#c084fc' }} /> Linear Trend Fit
                  </span>
                </div>
              </div>

              {/* CHART 2: Annual Duration & Intensity */}
              <div className="panel chart-panel">
                <div className="chart-heading">
                  <div>
                    <span className="section-kicker">ANNUAL CUMULATIVE DAYS</span>
                    <h3>Total Hazard Days per Year</h3>
                  </div>
                  <span className="chart-unit">DAYS / YEAR</span>
                </div>

                <div className="chart-wrap">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={chartData}>
                      <CartesianGrid strokeDasharray="3 5" stroke="#1d2e44" vertical={false} />
                      <XAxis
                        dataKey="year"
                        tick={{ fill: '#8ea5be', fontSize: 11 }}
                        tickLine={false}
                        axisLine={false}
                        minTickGap={24}
                      />
                      <YAxis
                        tick={{ fill: '#8ea5be', fontSize: 11 }}
                        tickLine={false}
                        axisLine={false}
                        allowDecimals={false}
                      />
                      <Tooltip
                        contentStyle={{
                          background: '#0d1827',
                          border: '1px solid #233954',
                          borderRadius: 10,
                          color: '#e7edf5',
                        }}
                      />
                      <Line
                        type="monotone"
                        dataKey="hazardDays"
                        name="Hazard Days"
                        stroke="#55c6b0"
                        strokeWidth={2.4}
                        dot={false}
                        activeDot={{ r: 5 }}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </div>

                <div className="chart-legend-box">
                  <span className="legend-item">
                    <span className="legend-swatch" style={{ background: '#55c6b0' }} /> Cumulative Annual Days
                  </span>
                </div>
              </div>
            </section>

            {/* INTERPRETATION / INSIGHTS PANEL */}
            <section className="panel insights-panel">
              <div className="chart-heading">
                <div>
                  <span className="section-kicker">03 / SCIENTIFIC SYNTHESIS</span>
                  <h3>What the Observations Indicate</h3>
                </div>
              </div>

              {analysis.insights?.headline && (
                <div className="insights-headline-banner">
                  {analysis.insights.headline}
                </div>
              )}

              <div className="insights-grid">
                <Insight
                  label="Decadal Comparison"
                  value={
                    analysis.insights?.decadalComparison?.difference == null
                      ? 'Single Period'
                      : `${analysis.insights.decadalComparison.difference > 0 ? '+' : ''}${analysis.insights.decadalComparison.difference} events/yr`
                  }
                  text={
                    analysis.insights?.decadalComparison?.firstDecadePeriod
                      ? `Compares early decade (${analysis.insights.decadalComparison.firstDecadePeriod}, avg ${analysis.insights.decadalComparison.firstDecadeAvg}/yr) against recent decade (${analysis.insights.decadalComparison.lastDecadePeriod}, avg ${analysis.insights.decadalComparison.lastDecadeAvg}/yr).`
                      : 'Decadal shift metrics require at least 10 years of historical data.'
                  }
                />

                <Insight
                  label="Peak Hazard Year"
                  value={
                    analysis.insights?.peakYear
                      ? `${analysis.insights.peakYear} (${analysis.insights.peakYearEvents} events)`
                      : 'None detected'
                  }
                  text="Calendar year recording the highest frequency of qualifying hazard events across the entire record."
                />

                <Insight
                  label="Threshold & Definition"
                  value={`${analysis.threshold} ${analysis.thresholdUnit || ''}`}
                  text={analysis.definition || 'Statistical climatology baseline applied.'}
                />
              </div>

              <div className="methodology-box">
                <h4>Methodology &amp; Climatological Assumptions</h4>
                <ul>
                  {analysis.assumptions?.map((assump, idx) => (
                    <li key={idx}>{assump}</li>
                  ))}
                  <li>
                    Data Source: {analysis.source} (Cache State: {analysis.cache || 'Fresh Query'}).
                  </li>
                  <li>
                    Linear regression slope ({analysis.trendSlopeEventsPerYear?.toFixed(4) ?? 0} events/year) reflects
                    ordinary least squares trend for descriptive risk evaluation, not long-term physical forecasting.
                  </li>
                </ul>
              </div>
            </section>

            {/* DETECTED EVENTS LOG */}
            <section className="panel events-panel">
              <div className="chart-heading">
                <div>
                  <span className="section-kicker">EVENT CATALOG</span>
                  <h3>Detected Hazard Events Log</h3>
                </div>
                <span className="chart-unit">{analysis.events.length} TOTAL EVENTS</span>
              </div>

              <div className="events-toolbar">
                <input
                  type="text"
                  placeholder="Filter by date (YYYY-MM)..."
                  value={eventSearch}
                  onChange={e => setEventSearch(e.target.value)}
                  className="events-search-input"
                />
                <span style={{ fontSize: 12, color: '#8ea5be' }}>
                  Showing {filteredEvents.length} of {analysis.events.length}
                </span>
              </div>

              {filteredEvents.length ? (
                <div className="table-scroll">
                  <table>
                    <thead>
                      <tr>
                        <th>EVENT #</th>
                        <th>START DATE</th>
                        <th>END DATE</th>
                        <th>DURATION</th>
                        <th>PEAK VALUE</th>
                        <th>INTENSITY / EXCESS</th>
                      </tr>
                    </thead>
                    <tbody>
                      {filteredEvents.slice(0, 100).map((event, idx) => (
                        <tr key={`${event.startDate}-${idx}`}>
                          <td>#{idx + 1}</td>
                          <td>{event.startDate}</td>
                          <td>{event.endDate}</td>
                          <td>{event.durationDays} days</td>
                          <td>
                            {event.maxTemperatureC != null
                              ? `${event.maxTemperatureC.toFixed(1)}°C`
                              : event.peakPrecipitationMm != null
                              ? `${event.peakPrecipitationMm.toFixed(1)} mm/day`
                              : `${event.durationDays} days dry`}
                          </td>
                          <td>
                            {event.meanExcessAboveThresholdC != null
                              ? `+${event.meanExcessAboveThresholdC.toFixed(1)}°C avg`
                              : event.totalPrecipitationMm != null
                              ? `${event.totalPrecipitationMm.toFixed(1)} mm total`
                              : '0.0 mm total'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <p style={{ margin: '20px 0', color: '#8ea5be', fontSize: 13 }}>
                  No qualifying events matched the current filter.
                </p>
              )}
            </section>
          </>
        )}

        <footer>
          <span>CLIMATE HAZARD TREND ANALYZER · DYGNIFY CASE STUDY</span>
          <span>Open-Meteo Archive · WMO Climate Standards · OLS Linear Regression</span>
        </footer>
      </main>
    </div>
  )
}

function Metric({
  icon,
  label,
  value,
  detail,
}: {
  icon: ReactNode
  label: string
  value: string
  detail: ReactNode
}) {
  return (
    <div className="panel metric-card">
      <div className="metric-top">
        {icon}
        <span>{label}</span>
      </div>
      <strong>{value}</strong>
      <div>{detail}</div>
    </div>
  )
}

function Insight({ label, value, text }: { label: string; value: string; text: string }) {
  return (
    <div className="insight-card">
      <span>{label}</span>
      <strong>{value}</strong>
      <p>{text}</p>
    </div>
  )
}

export default App
