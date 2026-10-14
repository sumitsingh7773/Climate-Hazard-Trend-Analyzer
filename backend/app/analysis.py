from datetime import date, timedelta
from math import isfinite

def percentile(values: list[float], pct: float) -> float:
    """Linear interpolation percentile calculation (inclusive sample percentile)."""
    if not values:
        raise ValueError("values list must not be empty for percentile calculation")
    sorted_vals = sorted(values)
    pos = (len(sorted_vals) - 1) * pct / 100.0
    lo = int(pos)
    hi = min(lo + 1, len(sorted_vals) - 1)
    return sorted_vals[lo] + (sorted_vals[hi] - sorted_vals[lo]) * (pos - lo)

def linear_regression(xs: list[int | float], ys: list[int | float]) -> dict:
    """Calculates ordinary least squares linear regression slope, intercept, R², and trend direction."""
    n = len(xs)
    if n < 2:
        return {
            "slope": 0.0,
            "intercept": 0.0,
            "r_squared": 0.0,
            "direction": "insufficient_data",
            "slope_per_decade": 0.0,
        }
    mx = sum(xs) / n
    my = sum(ys) / n
    ss_xx = sum((x - mx) ** 2 for x in xs)
    ss_yy = sum((y - my) ** 2 for y in ys)
    ss_xy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    if ss_xx == 0:
        return {
            "slope": 0.0,
            "intercept": round(my, 4),
            "r_squared": 0.0,
            "direction": "stable",
            "slope_per_decade": 0.0,
        }
    slope = ss_xy / ss_xx
    intercept = my - slope * mx
    r_squared = (ss_xy ** 2 / (ss_xx * ss_yy)) if (ss_xx * ss_yy) > 0 else 0.0
    direction = "increasing" if slope > 0.01 else ("decreasing" if slope < -0.01 else "stable")
    return {
        "slope": round(slope, 4),
        "intercept": round(intercept, 4),
        "r_squared": round(r_squared, 4),
        "direction": direction,
        "slope_per_decade": round(slope * 10.0, 3),
    }

def rolling_average(values: list[float], window: int) -> list[float]:
    """Calculates trailing rolling average for the given window size."""
    result = []
    for i in range(len(values)):
        sub = values[max(0, i - window + 1): i + 1]
        result.append(round(sum(sub) / len(sub), 2))
    return result

def calculate_decadal_comparison(yearly_stats: list[dict], metric_key: str = "events") -> dict:
    """Compares average values between the earliest and latest decade."""
    if len(yearly_stats) < 10:
        return {"firstDecadeAvg": None, "lastDecadeAvg": None, "diff": None}
    first_decade = yearly_stats[:10]
    last_decade = yearly_stats[-10:]
    first_avg = sum(y[metric_key] for y in first_decade) / len(first_decade)
    last_avg = sum(y[metric_key] for y in last_decade) / len(last_decade)
    diff = last_avg - first_avg
    return {
        "firstDecadePeriod": f"{first_decade[0]['year']}–{first_decade[-1]['year']}",
        "firstDecadeAvg": round(first_avg, 2),
        "lastDecadePeriod": f"{last_decade[0]['year']}–{last_decade[-1]['year']}",
        "lastDecadeAvg": round(last_avg, 2),
        "difference": round(diff, 2),
        "percentageChange": round((diff / first_avg) * 100, 1) if first_avg > 0 else None,
    }


# ==============================================================================
# 1. HEATWAVE ANALYSIS
# ==============================================================================

def analyze_heatwaves(records: list[dict], start_date: date, end_date: date) -> dict:
    clean = []
    invalid_count = 0
    for row in records:
        value = row.get("tmax_c")
        if value is not None and isinstance(value, (int, float)) and isfinite(value) and -90 <= value <= 65:
            clean.append({"date": date.fromisoformat(row["date"]), "tmax_c": float(value)})
        else:
            invalid_count += 1
    clean.sort(key=lambda r: r["date"])

    if len(clean) < 30:
        return {
            "hazard": "heatwave",
            "threshold": None,
            "thresholdC": None,
            "thresholdUnit": "°C",
            "totalEvents": 0,
            "totalHazardDays": 0,
            "totalHeatwaveDays": 0,
            "yearlyStats": [],
            "events": [],
            "trendSlopeEventsPerYear": None,
            "percentageChange": None,
            "regression": None,
            "insights": {"summary": "Insufficient valid temperature observations (minimum 30 required)."},
            "dataQuality": {"validDays": len(clean), "missingOrInvalidDays": invalid_count,
                            "warning": "At least 30 valid daily observations are needed."},
            "assumptions": ["Minimum 30 valid days required for statistical significance."],
        }

    temps = [r["tmax_c"] for r in clean]
    threshold = percentile(temps, 95)
    by_date = {r["date"]: r["tmax_c"] for r in clean}

    # Detect 3+ consecutive days strictly above 95th percentile
    events = []
    run = []
    cursor = start_date
    while cursor <= end_date:
        temp = by_date.get(cursor)
        if temp is not None and temp > threshold:
            run.append({"date": cursor.isoformat(), "tmax_c": temp})
        else:
            if len(run) >= 3:
                events.append(make_heatwave_event(run, threshold))
            run = []
        cursor += timedelta(days=1)
    if len(run) >= 3:
        events.append(make_heatwave_event(run, threshold))

    # Annual statistics
    yearly = {}
    for year in range(start_date.year, end_date.year + 1):
        yearly[year] = {
            "year": year,
            "events": 0,
            "hazardDays": 0,
            "heatwaveDays": 0,
            "meanEventDurationDays": 0.0,
            "maxDurationDays": 0,
            "peakIntensity": 0.0,
            "cumulativeDegreeDays": 0.0,
        }

    durations = {year: [] for year in yearly}
    for event in events:
        year = int(event["startDate"][:4])
        if year in yearly:
            yearly[year]["events"] += 1
            yearly[year]["heatwaveDays"] += event["durationDays"]
            yearly[year]["hazardDays"] += event["durationDays"]
            yearly[year]["cumulativeDegreeDays"] = round(
                yearly[year]["cumulativeDegreeDays"] + event["cumulativeDegreeDays"], 2
            )
            if event["maxTemperatureC"] > yearly[year]["peakIntensity"]:
                yearly[year]["peakIntensity"] = event["maxTemperatureC"]
            if event["durationDays"] > yearly[year]["maxDurationDays"]:
                yearly[year]["maxDurationDays"] = event["durationDays"]
            durations[year].append(event["durationDays"])

    for year, stats in yearly.items():
        ds = durations[year]
        stats["meanEventDurationDays"] = round(sum(ds) / len(ds), 2) if ds else 0.0

    points = list(yearly.values())
    years = [p["year"] for p in points]
    event_counts = [p["events"] for p in points]
    hazard_days = [p["hazardDays"] for p in points]

    # Rolling averages (3-year and 5-year)
    rolling_3yr = rolling_average([float(c) for c in event_counts], 3)
    rolling_5yr = rolling_average([float(c) for c in event_counts], 5)

    # Linear regression on yearly event counts
    reg = linear_regression(years, event_counts)
    reg_days = linear_regression(years, hazard_days)

    # Attach rolling averages and regression trend line to yearly stats
    for i, p in enumerate(points):
        p["rollingAvgEvents3Yr"] = rolling_3yr[i]
        p["rollingAvgEvents5Yr"] = rolling_5yr[i]
        p["trendLineEvents"] = round(reg["slope"] * p["year"] + reg["intercept"], 2)

    first_events = points[0]["events"] if points else 0
    last_events = points[-1]["events"] if points else 0
    percentage = round(((last_events - first_events) / first_events) * 100, 2) if first_events else None

    # Synthesis insights
    decadal = calculate_decadal_comparison(points, "events")
    peak_event = max(events, key=lambda e: e["maxTemperatureC"]) if events else None
    longest_event = max(events, key=lambda e: e["durationDays"]) if events else None
    peak_year = max(points, key=lambda p: p["events"]) if points else None

    insights = {
        "headline": (
            f"Heatwave frequency shows a {reg['direction']} trend of {reg['slope_per_decade']:+0.2f} events per decade (R²={reg['r_squared']})."
            if len(points) >= 2 else "Single-year analysis completed."
        ),
        "peakYear": peak_year["year"] if peak_year else None,
        "peakYearEvents": peak_year["events"] if peak_year else 0,
        "hottestEvent": {
            "date": peak_event["startDate"] if peak_event else None,
            "peakTemperatureC": peak_event["maxTemperatureC"] if peak_event else None,
            "excessC": peak_event["meanExcessAboveThresholdC"] if peak_event else None,
        } if peak_event else None,
        "longestEvent": {
            "startDate": longest_event["startDate"] if longest_event else None,
            "endDate": longest_event["endDate"] if longest_event else None,
            "durationDays": longest_event["durationDays"] if longest_event else None,
        } if longest_event else None,
        "decadalComparison": decadal,
        "trendDirection": reg["direction"],
        "slopePerDecade": reg["slope_per_decade"],
    }

    warning = None
    if invalid_count:
        warning = f"{invalid_count} days had missing, invalid, or implausible temperatures and were excluded."
    if first_events == 0:
        warning = (warning + " " if warning else "") + "Percentage change is omitted because the baseline year had zero heatwave events."

    return {
        "hazard": "heatwave",
        "hazardName": "Heatwave",
        "period": {"startDate": start_date.isoformat(), "endDate": end_date.isoformat()},
        "definition": "3 or more consecutive days with daily maximum temperature strictly exceeding the regional 95th-percentile threshold.",
        "threshold": round(threshold, 2),
        "thresholdC": round(threshold, 2),
        "thresholdUnit": "°C",
        "totalEvents": len(events),
        "totalHazardDays": sum(e["durationDays"] for e in events),
        "totalHeatwaveDays": sum(e["durationDays"] for e in events),
        "yearlyStats": points,
        "events": events,
        "trendSlopeEventsPerYear": reg["slope"],
        "trendSlopeDaysPerYear": reg_days["slope"],
        "percentageChange": percentage,
        "regression": reg,
        "insights": insights,
        "dataQuality": {
            "validDays": len(clean),
            "missingOrInvalidDays": invalid_count,
            "warning": warning,
        },
        "assumptions": [
            "The 95th percentile is calculated over the selected period's daily maximum temperatures.",
            "A qualifying heatwave event strictly requires 3 or more consecutive calendar days above the threshold.",
            "Missing or invalid days break a run rather than bridging across gaps.",
            "Events spanning calendar years are attributed to their starting year.",
        ],
    }

def make_heatwave_event(run: list[dict], threshold: float) -> dict:
    excesses = [r["tmax_c"] - threshold for r in run]
    return {
        "startDate": run[0]["date"],
        "endDate": run[-1]["date"],
        "durationDays": len(run),
        "maxTemperatureC": round(max(r["tmax_c"] for r in run), 2),
        "meanExcessAboveThresholdC": round(sum(excesses) / len(excesses), 2),
        "cumulativeDegreeDays": round(sum(excesses), 2),
    }


# ==============================================================================
# 2. HEAVY RAINFALL ANALYSIS
# ==============================================================================

def analyze_heavy_rainfall(records: list[dict], start_date: date, end_date: date) -> dict:
    """
    Detects extreme precipitation events.
    Documented meteorological threshold:
      - Wet day: daily precipitation >= 1.0 mm
      - Regional threshold: 95th percentile of wet days (WMO R95p index) or floor of 25.0 mm.
      - Heavy rainfall event: daily precipitation strictly exceeding the regional heavy rainfall threshold.
    """
    clean = []
    invalid_count = 0
    for row in records:
        val = row.get("prcp_mm")
        if val is not None and isinstance(val, (int, float)) and isfinite(val) and 0 <= val <= 1000:
            clean.append({"date": date.fromisoformat(row["date"]), "prcp_mm": float(val)})
        else:
            invalid_count += 1
    clean.sort(key=lambda r: r["date"])

    if len(clean) < 30:
        return {
            "hazard": "rainfall",
            "threshold": None,
            "thresholdUnit": "mm/day",
            "totalEvents": 0,
            "totalHazardDays": 0,
            "yearlyStats": [],
            "events": [],
            "trendSlopeEventsPerYear": None,
            "percentageChange": None,
            "regression": None,
            "insights": {"summary": "Insufficient valid precipitation observations."},
            "dataQuality": {"validDays": len(clean), "missingOrInvalidDays": invalid_count,
                            "warning": "At least 30 valid daily observations are needed."},
            "assumptions": ["Minimum 30 valid days required for statistical significance."],
        }

    wet_days = [r["prcp_mm"] for r in clean if r["prcp_mm"] >= 1.0]
    # If region has very few wet days, establish a standard 25mm heavy rain floor
    if wet_days:
        threshold = max(25.0, percentile(wet_days, 95))
    else:
        threshold = 25.0

    by_date = {r["date"]: r["prcp_mm"] for r in clean}
    events = []
    run = []
    cursor = start_date
    while cursor <= end_date:
        rain = by_date.get(cursor)
        if rain is not None and rain >= threshold:
            run.append({"date": cursor.isoformat(), "prcp_mm": rain})
        else:
            if run:
                events.append(make_rainfall_event(run, threshold))
                run = []
        cursor += timedelta(days=1)
    if run:
        events.append(make_rainfall_event(run, threshold))

    yearly = {}
    for year in range(start_date.year, end_date.year + 1):
        yearly[year] = {
            "year": year,
            "events": 0,
            "hazardDays": 0,
            "heavyRainDays": 0,
            "totalExtremeRainfallMm": 0.0,
            "maxDailyPrecipitationMm": 0.0,
            "peakIntensity": 0.0,
        }

    for event in events:
        year = int(event["startDate"][:4])
        if year in yearly:
            yearly[year]["events"] += 1
            yearly[year]["heavyRainDays"] += event["durationDays"]
            yearly[year]["hazardDays"] += event["durationDays"]
            yearly[year]["totalExtremeRainfallMm"] = round(
                yearly[year]["totalExtremeRainfallMm"] + event["totalPrecipitationMm"], 1
            )
            if event["peakPrecipitationMm"] > yearly[year]["maxDailyPrecipitationMm"]:
                yearly[year]["maxDailyPrecipitationMm"] = event["peakPrecipitationMm"]
                yearly[year]["peakIntensity"] = event["peakPrecipitationMm"]

    points = list(yearly.values())
    years = [p["year"] for p in points]
    event_counts = [p["events"] for p in points]
    reg = linear_regression(years, event_counts)
    reg_volume = linear_regression(years, [p["totalExtremeRainfallMm"] for p in points])

    rolling_3yr = rolling_average([float(c) for c in event_counts], 3)
    rolling_5yr = rolling_average([float(c) for c in event_counts], 5)

    for i, p in enumerate(points):
        p["rollingAvgEvents3Yr"] = rolling_3yr[i]
        p["rollingAvgEvents5Yr"] = rolling_5yr[i]
        p["trendLineEvents"] = round(reg["slope"] * p["year"] + reg["intercept"], 2)

    first_events = points[0]["events"] if points else 0
    last_events = points[-1]["events"] if points else 0
    percentage = round(((last_events - first_events) / first_events) * 100, 2) if first_events else None

    decadal = calculate_decadal_comparison(points, "events")
    peak_event = max(events, key=lambda e: e["peakPrecipitationMm"]) if events else None
    peak_year = max(points, key=lambda p: p["events"]) if points else None

    insights = {
        "headline": (
            f"Extreme precipitation frequency demonstrates a {reg['direction']} trend of {reg['slope_per_decade']:+0.2f} events per decade (R²={reg['r_squared']})."
            if len(points) >= 2 else "Single-year analysis completed."
        ),
        "peakYear": peak_year["year"] if peak_year else None,
        "peakYearEvents": peak_year["events"] if peak_year else 0,
        "wettestEvent": {
            "date": peak_event["startDate"] if peak_event else None,
            "peakPrecipitationMm": peak_event["peakPrecipitationMm"] if peak_event else None,
            "totalPrecipitationMm": peak_event["totalPrecipitationMm"] if peak_event else None,
        } if peak_event else None,
        "decadalComparison": decadal,
        "trendDirection": reg["direction"],
        "slopePerDecade": reg["slope_per_decade"],
    }

    return {
        "hazard": "rainfall",
        "hazardName": "Heavy Rainfall",
        "period": {"startDate": start_date.isoformat(), "endDate": end_date.isoformat()},
        "definition": f"Days with daily precipitation exceeding regional threshold ({round(threshold, 1)} mm/day, WMO R95p wet-day extreme percentile).",
        "threshold": round(threshold, 1),
        "thresholdUnit": "mm/day",
        "totalEvents": len(events),
        "totalHazardDays": sum(e["durationDays"] for e in events),
        "totalPrecipitationMm": round(sum(e["totalPrecipitationMm"] for e in events), 1),
        "yearlyStats": points,
        "events": events,
        "trendSlopeEventsPerYear": reg["slope"],
        "trendSlopeVolumePerYear": reg_volume["slope"],
        "percentageChange": percentage,
        "regression": reg,
        "insights": insights,
        "dataQuality": {
            "validDays": len(clean),
            "missingOrInvalidDays": invalid_count,
            "warning": "Missing rainfall days were excluded." if invalid_count else None,
        },
        "assumptions": [
            "Wet days are defined as days with precipitation >= 1.0 mm.",
            "Heavy rainfall threshold is the 95th percentile of wet days (minimum floor 25.0 mm).",
            "Consecutive heavy rainfall days are clustered into single multi-day extreme downpours.",
        ],
    }

def make_rainfall_event(run: list[dict], threshold: float) -> dict:
    amounts = [r["prcp_mm"] for r in run]
    return {
        "startDate": run[0]["date"],
        "endDate": run[-1]["date"],
        "durationDays": len(run),
        "peakPrecipitationMm": round(max(amounts), 1),
        "totalPrecipitationMm": round(sum(amounts), 1),
        "meanPrecipitationMm": round(sum(amounts) / len(amounts), 1),
    }


# ==============================================================================
# 3. DROUGHT ANALYSIS (Consecutive Dry Days / Meteorological Dry Spells)
# ==============================================================================

def analyze_drought(records: list[dict], start_date: date, end_date: date) -> dict:
    """
    Detects prolonged meteorological drought spells.
    Standard WMO / ETCCDI index:
      - Dry day: daily precipitation < 1.0 mm.
      - Severe dry spell: 15 or more consecutive dry days (CDD >= 15).
    """
    clean = []
    invalid_count = 0
    for row in records:
        val = row.get("prcp_mm")
        if val is not None and isinstance(val, (int, float)) and isfinite(val) and 0 <= val <= 1000:
            clean.append({"date": date.fromisoformat(row["date"]), "prcp_mm": float(val)})
        else:
            invalid_count += 1
    clean.sort(key=lambda r: r["date"])

    if len(clean) < 30:
        return {
            "hazard": "drought",
            "threshold": 15,
            "thresholdUnit": "consecutive dry days",
            "totalEvents": 0,
            "totalHazardDays": 0,
            "yearlyStats": [],
            "events": [],
            "trendSlopeEventsPerYear": None,
            "percentageChange": None,
            "regression": None,
            "insights": {"summary": "Insufficient precipitation observations."},
            "dataQuality": {"validDays": len(clean), "missingOrInvalidDays": invalid_count,
                            "warning": "At least 30 valid daily observations are needed."},
            "assumptions": ["Minimum 30 valid days required for statistical significance."],
        }

    threshold_dry_spell_days = 15
    by_date = {r["date"]: r["prcp_mm"] for r in clean}
    events = []
    run = []
    cursor = start_date
    while cursor <= end_date:
        rain = by_date.get(cursor)
        if rain is not None and rain < 1.0:
            run.append({"date": cursor.isoformat(), "prcp_mm": rain})
        else:
            if len(run) >= threshold_dry_spell_days:
                events.append({
                    "startDate": run[0]["date"],
                    "endDate": run[-1]["date"],
                    "durationDays": len(run),
                    "totalPrecipitationMm": round(sum(r["prcp_mm"] for r in run), 1),
                })
            run = []
        cursor += timedelta(days=1)
    if len(run) >= threshold_dry_spell_days:
        events.append({
            "startDate": run[0]["date"],
            "endDate": run[-1]["date"],
            "durationDays": len(run),
            "totalPrecipitationMm": round(sum(r["prcp_mm"] for r in run), 1),
        })

    yearly = {}
    for year in range(start_date.year, end_date.year + 1):
        yearly[year] = {
            "year": year,
            "events": 0,
            "hazardDays": 0,
            "totalDryDays": 0,
            "maxConsecutiveDryDays": 0,
            "peakIntensity": 0,
        }

    # Count total dry days per year
    for r in clean:
        yr = r["date"].year
        if yr in yearly and r["prcp_mm"] < 1.0:
            yearly[yr]["totalDryDays"] += 1

    for event in events:
        year = int(event["startDate"][:4])
        if year in yearly:
            yearly[year]["events"] += 1
            yearly[year]["hazardDays"] += event["durationDays"]
            if event["durationDays"] > yearly[year]["maxConsecutiveDryDays"]:
                yearly[year]["maxConsecutiveDryDays"] = event["durationDays"]
                yearly[year]["peakIntensity"] = event["durationDays"]

    points = list(yearly.values())
    years = [p["year"] for p in points]
    event_counts = [p["events"] for p in points]
    reg = linear_regression(years, event_counts)
    reg_dry_days = linear_regression(years, [p["totalDryDays"] for p in points])

    rolling_3yr = rolling_average([float(c) for c in event_counts], 3)
    rolling_5yr = rolling_average([float(c) for c in event_counts], 5)

    for i, p in enumerate(points):
        p["rollingAvgEvents3Yr"] = rolling_3yr[i]
        p["rollingAvgEvents5Yr"] = rolling_5yr[i]
        p["trendLineEvents"] = round(reg["slope"] * p["year"] + reg["intercept"], 2)

    first_events = points[0]["events"] if points else 0
    last_events = points[-1]["events"] if points else 0
    percentage = round(((last_events - first_events) / first_events) * 100, 2) if first_events else None

    decadal = calculate_decadal_comparison(points, "events")
    longest_spell = max(events, key=lambda e: e["durationDays"]) if events else None
    peak_year = max(points, key=lambda p: p["events"]) if points else None

    insights = {
        "headline": (
            f"Drought spells (>=15 consecutive dry days) exhibit a {reg['direction']} trend of {reg['slope_per_decade']:+0.2f} events per decade (R²={reg['r_squared']})."
            if len(points) >= 2 else "Single-year analysis completed."
        ),
        "peakYear": peak_year["year"] if peak_year else None,
        "peakYearEvents": peak_year["events"] if peak_year else 0,
        "longestSpell": {
            "startDate": longest_spell["startDate"] if longest_spell else None,
            "endDate": longest_spell["endDate"] if longest_spell else None,
            "durationDays": longest_spell["durationDays"] if longest_spell else None,
        } if longest_spell else None,
        "decadalComparison": decadal,
        "trendDirection": reg["direction"],
        "slopePerDecade": reg["slope_per_decade"],
    }

    return {
        "hazard": "drought",
        "hazardName": "Drought (Dry Spells)",
        "period": {"startDate": start_date.isoformat(), "endDate": end_date.isoformat()},
        "definition": f"Prolonged dry spells defined as 15 or more consecutive days with precipitation strictly < 1.0 mm (WMO Consecutive Dry Days index).",
        "threshold": threshold_dry_spell_days,
        "thresholdUnit": "consecutive dry days",
        "totalEvents": len(events),
        "totalHazardDays": sum(e["durationDays"] for e in events),
        "yearlyStats": points,
        "events": events,
        "trendSlopeEventsPerYear": reg["slope"],
        "trendSlopeDryDaysPerYear": reg_dry_days["slope"],
        "percentageChange": percentage,
        "regression": reg,
        "insights": insights,
        "dataQuality": {
            "validDays": len(clean),
            "missingOrInvalidDays": invalid_count,
            "warning": "Missing rainfall days were excluded." if invalid_count else None,
        },
        "assumptions": [
            "A dry day is defined as a day with precipitation < 1.0 mm.",
            "A drought spell is defined as 15+ consecutive dry days.",
            "A rainfall event of >= 1.0 mm terminates a drought spell.",
        ],
    }
