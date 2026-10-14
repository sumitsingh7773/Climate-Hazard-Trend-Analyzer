export type HazardType = 'heatwave' | 'rainfall' | 'drought'

export type Region = {
  name: string
  latitude: number
  longitude: number
  country?: string
}

export type YearStat = {
  year: number
  events: number
  hazardDays?: number
  heatwaveDays?: number
  heavyRainDays?: number
  totalDryDays?: number
  meanEventDurationDays?: number
  maxDurationDays?: number
  peakIntensity?: number
  cumulativeDegreeDays?: number
  totalExtremeRainfallMm?: number
  maxDailyPrecipitationMm?: number
  rollingAvgEvents3Yr?: number
  rollingAvgEvents5Yr?: number
  trendLineEvents?: number
}

export type HazardEvent = {
  startDate: string
  endDate: string
  durationDays: number
  maxTemperatureC?: number
  meanExcessAboveThresholdC?: number
  cumulativeDegreeDays?: number
  peakPrecipitationMm?: number
  totalPrecipitationMm?: number
  meanPrecipitationMm?: number
}

export type DecadalComparison = {
  firstDecadePeriod?: string
  firstDecadeAvg?: number
  lastDecadePeriod?: string
  lastDecadeAvg?: number
  difference?: number
  percentageChange?: number | null
}

export type AnalysisInsights = {
  headline?: string
  peakYear?: number | null
  peakYearEvents?: number
  hottestEvent?: {
    date: string | null
    peakTemperatureC: number | null
    excessC: number | null
  } | null
  wettestEvent?: {
    date: string | null
    peakPrecipitationMm: number | null
    totalPrecipitationMm: number | null
  } | null
  longestEvent?: {
    startDate: string | null
    endDate: string | null
    durationDays: number | null
  } | null
  longestSpell?: {
    startDate: string | null
    endDate: string | null
    durationDays: number | null
  } | null
  decadalComparison?: DecadalComparison
  trendDirection?: string
  slopePerDecade?: number
}

export type RegressionData = {
  slope: number
  intercept: number
  r_squared: number
  direction: string
  slope_per_decade: number
}

export type Analysis = {
  hazard: HazardType
  hazardName?: string
  period?: { startDate: string; endDate: string }
  region?: { latitude: number; longitude: number }
  definition?: string
  source?: string
  cache?: string
  threshold: number | null
  thresholdC?: number | null
  thresholdUnit?: string
  totalEvents: number
  totalHazardDays: number
  totalHeatwaveDays?: number
  totalPrecipitationMm?: number
  yearlyStats: YearStat[]
  events: HazardEvent[]
  trendSlopeEventsPerYear: number | null
  trendSlopeDaysPerYear?: number | null
  percentageChange: number | null
  regression?: RegressionData
  insights?: AnalysisInsights
  dataQuality: { validDays: number; missingOrInvalidDays: number; warning: string | null }
  assumptions?: string[]
}
