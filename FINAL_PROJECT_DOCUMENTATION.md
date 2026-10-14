# Climate Hazard Trend Analyzer — Final Project Documentation

## 1. Executive Summary & Architecture Overview

The **Climate Hazard Trend Analyzer** is a full-stack, data-driven climate intelligence system designed for empirical evaluation of long-term climate hazard trends: **Heatwaves**, **Extreme Heavy Rainfall**, and **Meteorological Drought**. 

The system accesses real, continuous historical reanalysis observations from the **Open-Meteo Historical Weather Archive API**, computes regional statistical baselines, detects multi-day hazard runs, fits Ordinary Least Squares (OLS) regression models, and generates synthesis insights for risk analysis, urban planning, and insurance benchmarking.

### High-Level Architecture Diagram

```
+-----------------------------------------------------------------------------------+
|                              FRONTEND (React 18 + TS)                             |
|  - Leaflet Map (Click-to-Pin)    - Recharts (Composed: Bars + Rolling Avg + Trend)|
|  - Multi-Hazard Switcher         - Custom Coordinates & Presets                   |
|  - Filterable Event Catalog      - Instant CSV & Print/PDF Export                 |
+-----------------------------------------------------------------------------------+
                                        |
                            HTTP / JSON (REST + CORS)
                                        v
+-----------------------------------------------------------------------------------+
|                               BACKEND (FastAPI / Python)                          |
|  - SlowAPI Rate Limiting (120/min)  - Pydantic Coordinate & Date Validation       |
|  - Hazard Algorithms (WMO / ETCCDI) - OLS Linear Regression & Moving Averages     |
+-----------------------------------------------------------------------------------+
                     |                                       |
                     v                                       v
+-----------------------------------+     +-----------------------------------------+
|     PERSISTENCE & CACHE LAYER     |     |           UPSTREAM DATA PROVIDER        |
| - MongoDB Atlas (when configured) |     | Open-Meteo Historical Archive API       |
| - Non-blocking In-Memory Fallback |     | (ERA5 / ERA5-Land Reanalysis, UTC)      |
| - Dual-variable storage (Tmax+Prc)|     | Variables: temperature_2m_max, prcp_sum |
+-----------------------------------+     +-----------------------------------------+
```

### Technology Stack
- **Frontend:** React 18.3, TypeScript 5.7, Vite 6.0, Recharts 2.15, Leaflet 1.9, Lucide React, Vanilla CSS.
- **Backend:** Python 3.12+, FastAPI 0.143, Uvicorn 0.54, SlowAPI 0.1.10, HTTPX 0.28, PyMongo 4.18, Pydantic 2.14, Pydantic-Settings 2.15.
- **External Data Source:** Open-Meteo Historical Weather Archive API (Reanalysis model data; no API key required).

---

## 2. End-to-End Workflow

1. **User Input / Selection:** User selects a hazard type (Heatwave, Extreme Rainfall, Drought), chooses a metropolitan preset or custom latitude/longitude (or uses browser geolocation / clicks the Leaflet map), and specifies a calendar year span (e.g., 1990–2020).
2. **Client Validation:** Frontend validates year bounds ($1940 \le \text{start} < \text{end} \le \text{Current Year} - 1$) and geographic limits ($\text{lat} \in [-90, 90], \text{lon} \in [-180, 180]$).
3. **Backend Request & Rate Limiting:** Request reaches FastAPI guarded by `slowapi` (120 req/min per IP) and strict query validation.
4. **Cache & Persistence Lookup:** Backend checks MongoDB (or in-memory cache fallback) for weather records covering `(locationKey, start_date, end_date)`.
5. **Upstream Data Ingestion:** If records are missing or incomplete, backend fetches daily `temperature_2m_max` and `precipitation_sum` simultaneously from Open-Meteo in a single query, storing both variables for instant subsequent cross-hazard queries.
6. **Climatological Analysis:**
   - Cleans data, excludes non-physical outliers, and handles calendar runs.
   - Calculates regional percentile / WMO threshold.
   - Identifies qualifying multi-day events and event-level severity metrics.
   - Aggregates annual statistics, 3-year/5-year moving averages, and OLS regression fit ($y = mx + c$, $R^2$, trend direction).
   - Generates automated decadal comparisons and synthesis insights.
7. **Rendering & Export:** Frontend renders dual responsive charts, key metric cards, insights banner, interactive map marker, and searchable event table, with options for CSV download and print-ready PDF reports.

---

## 3. Climatological Hazard Algorithms & Mathematical Formulas

### Mathematical Primitives
- **Sample Percentile (Linear Interpolation):**
  For sorted array $V = [v_0, v_1, \dots, v_{N-1}]$ and percentile $P \in (0, 100)$:
  $$i = (N - 1) \times \frac{P}{100}, \quad k = \lfloor i \rfloor, \quad f = i - k$$
  $$\text{Percentile}(V, P) = v_k + f \times (v_{k+1} - v_k) \quad (\text{with } v_N = v_{N-1})$$

- **Ordinary Least Squares (OLS) Linear Regression:**
  Given annual pairs $(x_t, y_t)$ where $x$ is year and $y$ is annual count:
  $$\bar{x} = \frac{1}{n}\sum x_t, \quad \bar{y} = \frac{1}{n}\sum y_t$$
  $$\text{Slope } m = \frac{\sum (x_t - \bar{x})(y_t - \bar{y})}{\sum (x_t - \bar{x})^2}, \quad \text{Intercept } c = \bar{y} - m\bar{x}$$
  $$R^2 = \frac{\left[\sum (x_t - \bar{x})(y_t - \bar{y})\right]^2}{\sum (x_t - \bar{x})^2 \sum (y_t - \bar{y})^2}, \quad \text{Slope per Decade} = 10 \times m$$

- **Trailing Rolling Moving Average (Window $W$):**
  $$\text{MA}_t(W) = \frac{1}{\min(t+1, W)} \sum_{k=\max(0, t-W+1)}^{t} y_k$$

---

### Hazard 1: Heatwave Analysis (`analyze_heatwaves`)
- **Metric Analyzed:** Daily maximum temperature ($T_{\max}$ in °C).
- **Threshold:** Regional 95th percentile ($P_{95}$) of valid daily maximum temperatures across the analysis period.
- **Event Condition:** Strictly $\ge 3$ consecutive calendar days with $T_{\max} > \text{Threshold}$.
- **Event Metrics:**
  - `durationDays`: Total consecutive qualifying days.
  - `maxTemperatureC`: Peak temperature recorded during the run.
  - `meanExcessAboveThresholdC`: Average temperature above threshold during event.
  - `cumulativeDegreeDays`: $\sum (T_{\max} - \text{Threshold})$ over all event days.
- **Annual Metrics:** Event count, total heatwave days, mean/max duration, peak temperature, cumulative degree days, 3-yr & 5-yr rolling averages, OLS regression fit.

### Hazard 2: Extreme Heavy Rainfall Analysis (`analyze_heavy_rainfall`)
- **Metric Analyzed:** Daily precipitation sum ($P_{\text{daily}}$ in mm).
- **Wet Day Definition:** $P_{\text{daily}} \ge 1.0\text{ mm}$ (WMO standard to filter gauge trace noise).
- **Threshold (WMO R95p):** 95th percentile of wet-day daily precipitation, with an enforced physical baseline floor of $25.0\text{ mm/day}$:
  $$\text{Threshold} = \max(25.0, P_{95}(\text{wet days}))$$
- **Event Condition:** Calendar days where $P_{\text{daily}} \ge \text{Threshold}$. Consecutive days cluster into multi-day downpours.
- **Event Metrics:** `durationDays`, `peakPrecipitationMm`, `totalPrecipitationMm`, `meanPrecipitationMm`.
- **Annual Metrics:** Heavy rainfall days, extreme event frequency, total extreme volume (mm), annual max daily precipitation, rolling averages, OLS regression fit.

### Hazard 3: Meteorological Drought Analysis (`analyze_drought`)
- **Metric Analyzed:** Daily precipitation sum ($P_{\text{daily}}$ in mm).
- **Dry Day Definition:** $P_{\text{daily}} < 1.0\text{ mm}$ (WMO standard).
- **Threshold (WMO Consecutive Dry Days):** Runs of $\ge 15$ consecutive dry days ($\text{CDD} \ge 15$).
- **Event Condition:** $\ge 15$ consecutive calendar days with precipitation strictly $< 1.0\text{ mm}$. Any day with $P_{\text{daily}} \ge 1.0\text{ mm}$ breaks the spell.
- **Event Metrics:** `startDate`, `endDate`, `durationDays` (consecutive dry days), `totalPrecipitationMm` ($\approx 0\text{ mm}$).
- **Annual Metrics:** Qualifying drought spells, total dry days per year, longest consecutive dry spell duration, rolling averages, OLS regression fit.

---

## 4. API Specification & Schemas

### Base URL
- Local: `http://127.0.0.1:8000`

### 1. `GET /api/health`
- **Description:** Verifies service health, active database mode, and cache statistics.
- **Response Schema:**
  ```json
  {
    "status": "healthy",
    "database": "connected | memory-cache-fallback | memory-cache-dev-mode",
    "cache_stats": {
      "weather_records_count": 0,
      "cached_analyses_count": 0,
      "db_mode": "string"
    }
  }
  ```

### 2. `GET /api/regions`
- **Description:** Returns preset metropolitan locations (Indian cities and international benchmarks).
- **Response Schema:**
  ```json
  {
    "regions": [
      { "name": "Patna, India", "latitude": 25.5941, "longitude": 85.1376, "country": "India" },
      { "name": "Delhi, India", "latitude": 28.6139, "longitude": 77.2090, "country": "India" }
    ]
  }
  ```

### 3. `GET /api/analysis/heatwave`
- **Query Parameters:**
  - `latitude` (float, `-90.0` to `90.0`)
  - `longitude` (float, `-180.0` to `180.0`)
  - `start_date` (ISO date `YYYY-MM-DD`)
  - `end_date` (ISO date `YYYY-MM-DD`, $\le \text{today} - 3\text{ days}$)
- **Response Schema:**
  ```json
  {
    "hazard": "heatwave",
    "hazardName": "Heatwave",
    "period": { "startDate": "YYYY-MM-DD", "endDate": "YYYY-MM-DD" },
    "threshold": 40.0,
    "thresholdUnit": "°C",
    "totalEvents": 29,
    "totalHazardDays": 161,
    "yearlyStats": [
      {
        "year": 2010,
        "events": 6,
        "hazardDays": 36,
        "meanEventDurationDays": 6.0,
        "rollingAvgEvents3Yr": 6.0,
        "trendLineEvents": 5.2
      }
    ],
    "events": [
      {
        "startDate": "YYYY-MM-DD",
        "endDate": "YYYY-MM-DD",
        "durationDays": 5,
        "maxTemperatureC": 40.5,
        "meanExcessAboveThresholdC": 0.4,
        "cumulativeDegreeDays": 2.0
      }
    ],
    "regression": {
      "slope": -0.3545,
      "intercept": 717.05,
      "r_squared": 0.2284,
      "direction": "decreasing",
      "slope_per_decade": -3.545
    },
    "insights": {
      "headline": "Heatwave frequency shows a decreasing trend...",
      "peakYear": 2010,
      "peakYearEvents": 6,
      "decadalComparison": { ... }
    },
    "dataQuality": {
      "validDays": 4018,
      "missingOrInvalidDays": 0,
      "warning": null
    },
    "source": "Open-Meteo Historical Weather API",
    "cache": "weather-fetched | weather-cache-hit | analysis-hit"
  }
  ```

### 4. `GET /api/analysis/rainfall`
- Accepts same query parameters; executes heavy rainfall analysis ($P_{95}$ wet-day threshold).

### 5. `GET /api/analysis/drought`
- Accepts same query parameters; executes Consecutive Dry Days analysis ($\text{CDD} \ge 15$).

### 6. `GET /api/analysis`
- Generic router endpoint taking query parameter `hazard=heatwave|rainfall|drought`.

---

## 5. Frontend UI Features

- **Multi-Hazard Tabs:** Clean switcher between Heatwaves (Flame / orange theme), Extreme Rainfall (CloudRain / sky-blue theme), and Drought Spells (Sun / amber theme).
- **Location Selector:** Preset metropolitan dropdown, manual Latitude/Longitude number inputs with coordinate syncing, and browser geolocation ("My Location").
- **Interactive Leaflet Map:** Pinned to current coordinates with Carto voyager tiles, popup badge, and click-to-pin coordinate repositioning.
- **Quick Year Range Chips:** One-click shortcuts for `1990–2020 (30 Yrs)`, `2000–2023`, `Past 20 Yrs`, and `Past 10 Yrs`.
- **Dual Composed Charts:**
  1. *Annual Frequency Composed Chart:* Annual event bars with overlaid 3-year rolling average curve and dashed linear regression trendline.
  2. *Annual Cumulative Hazard Days Chart:* Annual total days spent in extreme events.
- **Metric Cards:** Total events, total hazard days, regional threshold, trend slope per year/decade with status badges (↗ INCREASING, ↘ DECREASING, → STABLE).
- **Scientific Synthesis Panel:** Plain-English summary headline, decadal comparison metric, peak hazard year, and methodology disclosures.
- **Filterable Event Catalog:** Searchable table listing all individual events with dates, durations, peak values, and anomalies.
- **Exports:** One-click CSV export (aggregates + event logs) and browser-optimized `@media print` PDF generation.

---

## 6. Setup Commands & Environment Variables

### Environment Variables

#### Backend (`backend/.env`)
| Variable | Required | Default | Purpose |
|---|---|---|---|
| `MONGODB_URI` | Optional | `None` (in-memory) | MongoDB connection string (Atlas or local) |
| `MONGODB_DATABASE` | Optional | `climate_hazard_analyzer` | Database name |
| `FRONTEND_ORIGIN` | Optional | `http://localhost:5173` | CORS allowed origin |
| `API_RATE_LIMIT` | Optional | `120/minute` | Rate limit per client IP |

#### Frontend (`frontend/.env`)
| Variable | Required | Default | Purpose |
|---|---|---|---|
| `VITE_API_BASE_URL` | Optional | `http://127.0.0.1:8000` | Target FastAPI backend URL |

### Setup Instructions

#### Backend Setup
```bash
cd backend
python -m venv .venv

# Activate Virtual Environment:
# Windows (PowerShell): .\.venv\Scripts\Activate.ps1
# Windows (CMD):        .venv\Scripts\activate.bat
# Linux / macOS:        source .venv/bin/activate

pip install -r requirements.txt
copy .env.example .env     # On Windows (use cp on Linux/macOS)
uvicorn app.main:app --reload --port 8000
```

#### Frontend Setup
```bash
cd frontend
npm install
copy .env.example .env     # On Windows (use cp on Linux/macOS)
npm run dev
```

---

## 7. Security, Validation, & Resilience

- **Rate Limiting:** Managed via `slowapi` at 120 requests/minute per client IP to safeguard upstream Open-Meteo resources.
- **CORS Configuration:** Explicitly configured with origin regex `^https?://(localhost|127\.0\.0\.1)(:\d+)?$` and allowed methods/headers, permitting smooth cross-origin communication without CORS 405 errors.
- **Input Boundaries:**
  - Latitude: $-90.0 \le \text{lat} \le 90.0$ (returns HTTP 422 on violation).
  - Longitude: $-180.0 \le \text{lon} \le 180.0$ (returns HTTP 422 on violation).
  - Date ordering: $\text{start\_date} \le \text{end\_date}$ (returns HTTP 400 on violation).
  - Maximum window: 70 years maximum range (returns HTTP 400 on violation).
  - Archive publication lag: $\text{end\_date} \le \text{today} - 3\text{ days}$ (returns HTTP 400 on violation).
- **Non-Blocking MongoDB Fallback:** MongoDB connectivity is tested with a 2500ms timeout (`serverSelectionTimeoutMS=2500`). Any DNS failure or unconfigured credentials automatically fail open to high-performance in-memory caching without throwing 500 errors.

---

## 8. Test Execution & Build Results

### Backend Automated Test Suite (19 Tests)
Command: `python -m unittest discover -s tests`  
**Result:** **19 Passed, 0 Failed, 0 Errors** (Execution time: 0.169s)

```
Ran 19 tests in 0.169s
OK
```
- Math primitives verified: `test_percentile`, `test_linear_regression`, `test_rolling_average`.
- Hazard detection verified: `test_heatwave_detected_after_three_hot_days`, `test_heatwave_two_days_not_qualifying`, `test_heavy_rainfall_detection`, `test_drought_consecutive_dry_days_detection`.
- API endpoints & validation verified: `test_root_endpoint`, `test_health_endpoint`, `test_regions_endpoint`, `test_validation_date_order`, `test_validation_future_date`, `test_validation_latitude_range`, `test_validation_longitude_range`, `test_validation_max_range_70_years`.
- Integration & mock tests verified: `test_mocked_heatwave_analysis_endpoint`, `test_mocked_rainfall_analysis_endpoint`, `test_mocked_drought_analysis_endpoint`, `test_db_status_and_cache_stats`.

### Frontend Type-Check & Production Build
Command: `tsc -b && vite build` in `frontend`  
**Result:** **Exit Code 0** (Build time: 9.60s)
- TypeScript: 0 errors.
- Production assets generated in `frontend/dist/` (`index.html`, `index-*.css`, `index-*.js`).

---

## 9. Verified Sample Results (Live Open-Meteo Data)

**Location:** Patna, India (`25.594° N`, `85.138° E`)  
**Time Window:** `2010-01-01` to `2020-12-31` (11 years / 4,018 calendar days)

| Hazard Category | Threshold Computed | Events Detected | Total Days | Trend Slope | $R^2$ Fit | Record Event Observed |
|---|---|---|---|---|---|---|
| **Heatwave** | $40.0^\circ\text{C}$ ($P_{95}$ Daily Max) | 29 events | 161 days | $-0.355\text{ ev/yr}$ ($-3.55/\text{dec}$) | $0.228$ | $40.8^\circ\text{C}$ (2010-04-02 to 2010-04-07, 6 days) |
| **Heavy Rainfall** | $29.4\text{ mm/day}$ ($P_{95}$ Wet-Day) | 40 events | 62 days | $+0.464\text{ ev/yr}$ ($+4.64/\text{dec}$) | $0.556$ | $120.0\text{ mm}$ (2010-07-10 to 2010-07-12, peak $53.3\text{ mm}$) |
| **Drought (Dry Spells)**| $15\text{ dry days}$ ($\text{CDD} \ge 15$) | 51 events | 1,952 days | $-0.064\text{ ev/yr}$ ($-0.64/\text{dec}$) | $0.052$ | 42 consecutive dry days (2010-01-01 to 2010-02-11) |

---

## 10. Climatological Assumptions & Known Limitations

1. **Sample Baseline vs. Fixed Reference Normal:**
   - *Current Implementation (Sample Baseline):* The 95th percentile is computed over the selected period. This makes analysis self-contained across any custom time window.
   - *Limitation / Climatological Note:* In long-term climate attribution, computing percentiles over a warming period can slightly elevate the threshold, masking part of the frequency trend. A fixed 30-year normal (e.g., 1991–2020) is recommended for production climatological attribution.
2. **Spatial Resolution:**
   - Point coordinates are used for analysis. Bounding-box spatial aggregation and polygon averaging are not included in the current MVP.
3. **Data Source Nature:**
   - Open-Meteo Historical Archive provides model/reanalysis data (ERA5/ERA5-Land). Values represent grid reanalysis estimates rather than raw uncorrected ground station sensor records.
4. **OLS Trend Scope:**
   - Linear regression slopes are descriptive statistical summaries of historical change; they do not establish physical causation or substitute for CMIP6 climate model projections.

---

## 11. Production Deployment Guidelines

*(Note: In accordance with instructions, actual deployment has NOT been executed and remains pending user approval).*

### Backend (Docker / Render / Railway / AWS ECS)
1. **Containerize:** Use standard Python slim container:
   ```dockerfile
   FROM python:3.12-slim
   WORKDIR /app
   COPY requirements.txt .
   RUN pip install --no-cache-dir -r requirements.txt
   COPY app/ ./app/
   EXPOSE 8000
   CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
   ```
2. **Environment Variables:** Provide `MONGODB_URI`, `FRONTEND_ORIGIN`, and `API_RATE_LIMIT`.

### Frontend (Vercel / Netlify / Cloudflare Pages)
1. Set build command: `npm run build`.
2. Set output directory: `dist`.
3. Set environment variable: `VITE_API_BASE_URL=https://<your-backend-api-url>`.

---

## 12. AI Tools Usage Disclosure

In compliance with case study standards:
- **AI Coding Assistant (Antigravity):** Used for code refactoring, TypeScript type expansion, implementing WMO climate formulas (R95p, Consecutive Dry Days), structuring test cases, diagnosing CORS/process port collisions, and compiling documentation.
- All generated code was executed, tested, and validated against live Open-Meteo APIs and verified through interactive browser testing.

---

## 13. Final Submission Checklist

- [x] Backend route `GET /api/regions` implemented and tested with 12 metropolitan presets.
- [x] Backend route `GET /api/analysis/heatwave` implemented with 3+ day 95th-percentile logic.
- [x] Backend routes for Extreme Rainfall and Drought implemented with standard WMO thresholds.
- [x] CORS middleware configured to handle all local and production origins without 405 preflight errors.
- [x] Real historical weather data fetched from Open-Meteo with dual-variable caching.
- [x] MongoDB Atlas persistence supported with graceful, non-blocking in-memory fallback.
- [x] Moving averages (3-yr, 5-yr) and OLS linear regression ($y = mx + c$, $R^2$) computed.
- [x] React UI completed with presets, custom lat/lon inputs, interactive Leaflet map, dual charts, and event table.
- [x] CSV and PDF print report export implemented.
- [x] 19 automated backend tests passing (`Ran 19 tests in 0.169s - OK`).
- [x] Frontend type-checking and production build passing (`tsc -b && vite build - OK`).
- [x] Live browser verification completed (dashboard active on `localhost:5173`).
- [ ] Production cloud deployment (marked as **PENDING USER APPROVAL**).
