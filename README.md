# Climate Hazard Trend Analyzer

A production-grade full-stack climate intelligence platform for detecting and analyzing long-term historical trends in **Heatwaves**, **Extreme Heavy Rainfall**, and **Meteorological Drought**. Built with **React + TypeScript + Vite** on the frontend and **FastAPI + Python** on the backend, utilizing empirical historical observations from the **Open-Meteo Historical Weather Archive API**.

---

## 🌟 Key Features

1. **Multi-Hazard Climatological Detection:**
   - **Heatwaves:** 3 or more consecutive calendar days with daily maximum temperature strictly exceeding the regional 95th-percentile threshold.
   - **Extreme Heavy Rainfall:** Days with precipitation exceeding the regional 95th percentile of wet days (WMO R95p index with a 25.0 mm/day floor) clustered into multi-day extreme downpours.
   - **Meteorological Drought (Dry Spells):** Runs of 15 or more Consecutive Dry Days (CDD, daily rainfall < 1.0 mm) based on WMO drought indices.

2. **Advanced Statistical & Trend Modeling:**
   - **Annual Aggregates:** Yearly event frequency, cumulative hazard days, peak intensity, and duration metrics.
   - **Rolling Averages:** 3-year and 5-year moving averages to filter out interannual climate noise (e.g., ENSO cycles).
   - **Linear Regression Trends:** Ordinary least squares (OLS) regression slope ($y = mx + c$), rate per decade, $R^2$ goodness-of-fit, and trend direction.
   - **Decadal Comparisons:** Baseline comparisons comparing the early decade against the most recent decade.
   - **Automated Synthesis Insights:** Algorithmic interpretation highlighting peak risk years, record events, and decadal percentage shifts.

3. **Interactive & Responsive UI:**
   - **Geographic Selection:** Presets for major Indian cities (Patna, Delhi, Mumbai, Kolkata, Ranchi, Chennai, Bengaluru, Ahmedabad) and global benchmark cities (London, Phoenix, Tokyo, Dubai), plus custom coordinate inputs and browser geolocation ("My Location").
   - **Interactive Leaflet Map:** Visual geographic coordinate preview with click-to-pin coordinate repositioning and custom pulsing radar pin.
   - **Dual Composed Charts:** Annual event frequency bar chart overlaid with rolling average and linear regression trendlines, alongside annual cumulative duration charts.
   - **Event Log Catalog:** Filterable, searchable table of all individual qualifying events with duration, peak values, and anomalies.
   - **Dual Export:** Instant CSV export (yearly stats + event catalog) and browser-optimized PDF/Print executive summary reports.

4. **Resilient Data Caching & Persistence:**
   - Persistent storage in MongoDB Atlas when `MONGODB_URI` is configured.
   - **Automatic Zero-Config Fallback:** If MongoDB is omitted or unreachable, seamlessly falls back to high-performance in-memory caching with non-blocking timeouts (2.5s).
   - Cache tagging (`analysis-hit`, `weather-cache-hit`, `weather-fetched`) displayed live in the application.

5. **Security & Input Validation:**
   - Latitude (-90° to +90°) and Longitude (-180° to +180°) validation.
   - Date range constraints: chronological order, maximum 70-year analysis window, and 3-day archive lag enforcement.
   - SlowAPI rate limiting (120 requests/minute per client).
   - Permissive CORS configuration supporting localhost, 127.0.0.1 across ports, and environment-specified origins.

---

## 🏗️ Architecture & Tech Stack

```
climate-hazard-analyzer/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── config.py         # Pydantic BaseSettings & env configuration
│   │   ├── db.py             # MongoDB client with auto memory fallback & cache tracking
│   │   ├── weather.py        # Open-Meteo HTTPX client (temperature + precipitation)
│   │   ├── analysis.py       # Climatological algorithms (Heatwave, Rain, Drought, Regression)
│   │   └── main.py           # FastAPI application, CORS, rate limiting, endpoints
│   ├── tests/
│   │   ├── test_analysis.py  # Unit tests for percentiles, regression, rolling avg, hazard logic
│   │   └── test_api.py       # Integration tests with FastAPI TestClient and mock weather data
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   └── LocationMap.tsx # Interactive Leaflet map with click-to-pin coordinate picker
│   │   ├── api.ts            # Fetch client for regions, health, and multi-hazard analysis
│   │   ├── types.ts          # Comprehensive TypeScript interfaces
│   │   ├── styles.css        # Modern climate intelligence design tokens & print media
│   │   ├── App.tsx           # Full interactive dashboard
│   │   └── main.tsx
│   ├── package.json
│   ├── tsconfig.json
│   └── vite.config.ts
└── README.md
```

- **Frontend:** React 18, TypeScript, Vite, Recharts, Leaflet, Lucide React, Vanilla CSS.
- **Backend:** Python 3.12+, FastAPI, Uvicorn, SlowAPI, HTTPX, PyMongo, Pydantic-Settings.
- **External Data:** Open-Meteo Historical Weather Archive API.

---

## 🚀 Local Setup & Installation

### Prerequisites
- Python 3.11+
- Node.js 18+ and npm
- Windows PowerShell, CMD, macOS, or Linux Terminal

---

### 1. Backend Setup

1. Open a terminal in the `backend` folder:
   ```bash
   cd backend
   ```

2. Create and activate a Python virtual environment:
   - **Windows (PowerShell):**
     ```powershell
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```
   - **Windows (CMD):**
     ```cmd
     py -m venv .venv
     .venv\Scripts\activate.bat
     ```
   - **macOS / Linux:**
     ```bash
     python3 -m venv .venv
     source .venv/bin/activate
     ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. *(Optional)* Configure environment variables:
   ```bash
   # Create .env from template (defaults to in-memory cache if MONGODB_URI is left blank)
   copy .env.example .env     # Windows
   # cp .env.example .env     # Linux / macOS
   ```
   *Note: If `MONGODB_URI` is not set or cluster is unreachable, the system automatically uses in-memory caching.*

5. Run the backend development server:
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```
   - Interactive Swagger API docs: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
   - API Health check: [http://127.0.0.1:8000/api/health](http://127.0.0.1:8000/api/health)

---

### 2. Frontend Setup

1. Open a second terminal in the `frontend` folder:
   ```bash
   cd frontend
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Run the Vite development server:
   ```bash
   npm run dev
   ```
   - Access the dashboard at: [http://localhost:5173](http://localhost:5173)

---

## 🧪 Automated Testing & Production Build

### Running Backend Tests
Execute the comprehensive unit and integration test suite (19 test cases):
```bash
cd backend
python -m unittest discover -s tests
```
Tests cover:
- Mathematical sample percentile calculation (linear interpolation).
- Ordinary least squares linear regression (slope, intercept, $R^2$, trend direction).
- 3-year and 5-year rolling moving averages.
- Heatwave detection (validating 3+ consecutive day threshold and filtering non-qualifying 2-day spikes).
- Extreme heavy rainfall detection and WMO threshold floors.
- Prolonged drought spell detection and Consecutive Dry Days (CDD).
- FastAPI endpoints (`/api/regions`, `/api/health`, `/api/analysis/*`).
- Input validation (date ordering, latitude/longitude bounds, future dates, max 70-year windows).
- Mocked external weather requests and database fallback behavior.

### Running Frontend Type-Check & Build
```bash
cd frontend
npm run build
```
Builds production-optimized assets with strict TypeScript type-checking (`tsc -b && vite build`).

---

## 📡 API Reference

### `GET /api/health`
Returns system status, active database mode, and cached record counts.
- **Sample Response:**
  ```json
  {
    "status": "healthy",
    "database": "connected",
    "cache_stats": {
      "weather_records_count": 11323,
      "cached_analyses_count": 4,
      "db_mode": "connected"
    }
  }
  ```

### `GET /api/regions`
Returns preset list of Indian and international metropolitan coordinates.

### `GET /api/analysis/heatwave`
Analyzes extreme heatwave events over the requested coordinates and date window.
- **Query Parameters:**
  - `latitude` (float, `-90.0` to `90.0`, default `25.5941`)
  - `longitude` (float, `-180.0` to `180.0`, default `85.1376`)
  - `start_date` (ISO date `YYYY-MM-DD`, default `1990-01-01`)
  - `end_date` (ISO date `YYYY-MM-DD`, default `2020-12-31`)
- **Key Output Properties:**
  - `hazard`: `"heatwave"`
  - `threshold`: Regional 95th-percentile daily max temperature in °C.
  - `totalEvents`: Number of detected 3+ consecutive day heatwave runs.
  - `totalHazardDays`: Cumulative days spent inside qualifying heatwave runs.
  - `yearlyStats`: Array of annual records containing `year`, `events`, `hazardDays`, `rollingAvgEvents3Yr`, `rollingAvgEvents5Yr`, `trendLineEvents`.
  - `events`: Array of individual detected events with `startDate`, `endDate`, `durationDays`, `maxTemperatureC`, `meanExcessAboveThresholdC`, `cumulativeDegreeDays`.
  - `regression`: Trend object with `slope`, `slope_per_decade`, `r_squared`, and `direction`.
  - `insights`: Automated scientific findings with decadal comparison, peak year, record event, and headline takeaway.

### `GET /api/analysis/rainfall`
Analyzes extreme heavy rainfall events using Open-Meteo `precipitation_sum` and WMO R95p wet-day percentiles.

### `GET /api/analysis/drought`
Analyzes meteorological drought spells using Consecutive Dry Days (CDD >= 15 days).

### `GET /api/analysis`
Generic router endpoint taking `hazard=heatwave|rainfall|drought` parameter.

---

## 📊 Climatological Logic, Standards, & Assumptions

### 1. Heatwave Percentile Baseline & Climatology
- **Percentile Calculation Method:**
  The threshold is computed using linear interpolation on the sorted array of valid daily maximum temperatures:
  $$i = (N - 1) \times \frac{95}{100}$$
  $$\text{Threshold} = v_{\lfloor i \rfloor} + (v_{\lceil i \rceil} - v_{\lfloor i \rfloor}) \times (i - \lfloor i \rfloor)$$
  This matches standard inclusive sample percentile algorithms used in meteorological analysis.

- **Sample-Period Baseline vs. Fixed Climatological Reference Baseline:**
  - **MVP Approach (Sample Baseline):** In this MVP, the 95th percentile is computed across the user-selected date window. This ensures self-contained analysis for any custom location and duration without requiring a separate pre-download of a fixed historical period.
  - **Production Recommendation (Fixed Baseline):** In professional climatological attribution (WMO standards), thresholds are typically computed against a fixed 30-year reference normal (e.g., 1961–1990 or 1991–2020). Using a fixed baseline ensures that a warming trend in recent decades does not inflate the threshold and mask the true increase in heatwave frequency.
  - **Production Architecture Path:** To implement a fixed baseline, configure a background worker that fetches the 1991–2020 climatological normal for the queried coordinate once, computes $P_{95}$, and applies this fixed threshold across any target query window.

- **Heatwave Event Definition:** Strictly 3 or more consecutive calendar days where daily maximum temperature strictly exceeds the threshold ($T_{\max} > \text{Threshold}$).
- **Missing Data Handling:** Missing or invalid temperatures break a consecutive run. They are not imputed or bridged.
- **Calendar Boundary Attribution:** Heatwave events spanning across December 31 and January 1 are attributed to their starting year.
- **Percentage Change Omission:** When the baseline year records 0 events, percentage change is formally omitted (rather than computing division by zero) and annotated in the data quality response.

### 2. Heavy Rainfall Climatology (WMO Standards)
- **Wet Day Definition:** Days with precipitation $\ge 1.0\text{ mm}$ (WMO standard to filter gauge trace noise).
- **Extreme Rainfall Threshold:** 95th percentile of wet-day precipitation with an enforced physical baseline floor of $25.0\text{ mm/day}$ (WMO R95p / R25mm index).
- **Event Clustering:** Consecutive heavy precipitation days are clustered into single multi-day extreme downpours to capture atmospheric river / monsoon deluge events.

### 3. Drought Climatology (Consecutive Dry Days)
- **Dry Day Definition:** Days with precipitation $< 1.0\text{ mm}$.
- **Meteorological Drought Spell:** Runs of 15 or more Consecutive Dry Days (CDD $\ge 15$).
- **Termination:** A calendar day with precipitation $\ge 1.0\text{ mm}$ terminates the dry spell.

### 4. Trend Regression Scope
- Ordinary Least Squares (OLS) linear regression ($y = mx + c$) is computed over annual event frequencies to describe historical trajectory and rate of change per decade.
- R-squared ($R^2$) measures goodness-of-fit.
- Regression slopes are descriptive indicators of historical trend and do not establish physical causation or predictive climate projections.

---

## 🛡️ Security & Performance Considerations

- **Rate Limiting:** Managed by `slowapi` limiting clients to 120 requests/minute to protect upstream Open-Meteo quota.
- **Fail-Safe DB Driver:** MongoDB connectivity initialization uses a 2500ms timeout; any connection failures (e.g. unconfigured Atlas credentials or network drops) fail open to in-memory caching without dropping client requests.
- **Payload Validation:** Strict Pydantic query validation rejects out-of-bounds coordinates, inverted dates, and queries beyond the supported 70-year archive window.
- **Client Cache Reusability:** Weather records store both `temperature_2m_max` and `precipitation_sum` simultaneously, allowing switching between Heatwave, Rainfall, and Drought modes for the same location with instant cache hits.

---

## 🚢 Production Deployment Guidelines

### 1. Backend Deployment (Docker / Render / Railway / AWS ECS)

#### Dockerfile Example
```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app/ ./app/
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### Environment Variables
| Variable | Description | Default / Example |
|---|---|---|
| `MONGODB_URI` | MongoDB Atlas connection string | `mongodb+srv://user:pass@cluster.mongodb.net/?retryWrites=true` |
| `MONGODB_DATABASE` | Database name | `climate_hazard_analyzer` |
| `FRONTEND_ORIGIN` | Allowed CORS origins (comma-separated or single) | `https://your-frontend-domain.com` |
| `API_RATE_LIMIT` | Max requests per minute per IP | `120/minute` |

### 2. Frontend Deployment (Vercel / Netlify / Cloudflare Pages)

#### Build Settings
- **Build Command:** `npm run build`
- **Output Directory:** `dist`
- **Node Version:** 18+

#### Environment Variables
| Variable | Description | Example |
|---|---|---|
| `VITE_API_BASE_URL` | Deployed backend URL | `https://your-backend-api.onrender.com` |

---
