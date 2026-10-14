import unittest
from datetime import date, timedelta
from app.analysis import (
    analyze_heatwaves,
    analyze_heavy_rainfall,
    analyze_drought,
    percentile,
    linear_regression,
    rolling_average,
)

class AnalysisMathTests(unittest.TestCase):
    def test_percentile(self):
        self.assertEqual(percentile([1.0, 2.0, 3.0, 4.0], 50), 2.5)
        self.assertEqual(percentile([10.0, 20.0, 30.0, 40.0, 50.0], 90), 46.0)

    def test_linear_regression(self):
        xs = [2000, 2001, 2002, 2003, 2004]
        ys = [2.0, 4.0, 6.0, 8.0, 10.0]
        reg = linear_regression(xs, ys)
        self.assertAlmostEqual(reg["slope"], 2.0, places=3)
        self.assertAlmostEqual(reg["r_squared"], 1.0, places=3)
        self.assertEqual(reg["direction"], "increasing")

    def test_rolling_average(self):
        vals = [10.0, 20.0, 30.0, 40.0, 50.0]
        roll_3 = rolling_average(vals, 3)
        self.assertEqual(roll_3[0], 10.0)
        self.assertEqual(roll_3[1], 15.0)  # (10+20)/2
        self.assertEqual(roll_3[2], 20.0)  # (10+20+30)/3
        self.assertEqual(roll_3[3], 30.0)  # (20+30+40)/3
        self.assertEqual(roll_3[4], 40.0)  # (30+40+50)/3

class HeatwaveAnalysisTests(unittest.TestCase):
    def test_heatwave_detected_after_three_hot_days(self):
        start = date(2020, 1, 1)
        records = []
        # 60 baseline days and 3 high-temperature days keep 95th percentile below 45C
        for i in range(63):
            day = start + timedelta(days=i)
            temp = 20.0 + (i % 5)
            if i in (30, 31, 32):
                temp = 45.0
            records.append({"date": day.isoformat(), "tmax_c": temp})
        result = analyze_heatwaves(records, start, start + timedelta(days=62))
        self.assertGreater(result["thresholdC"], 20.0)
        self.assertEqual(result["totalEvents"], 1)
        self.assertEqual(result["totalHeatwaveDays"], 3)
        self.assertEqual(result["events"][0]["durationDays"], 3)
        self.assertIn("rollingAvgEvents3Yr", result["yearlyStats"][0])
        self.assertIn("insights", result)

    def test_heatwave_two_days_not_qualifying(self):
        start = date(2020, 1, 1)
        records = []
        # Only 2 days above threshold -> should NOT qualify as 3+ day heatwave
        for i in range(60):
            day = start + timedelta(days=i)
            temp = 20.0 + (i % 4)
            if i in (20, 21):
                temp = 45.0
            records.append({"date": day.isoformat(), "tmax_c": temp})
        result = analyze_heatwaves(records, start, start + timedelta(days=59))
        self.assertEqual(result["totalEvents"], 0)
        self.assertEqual(result["totalHeatwaveDays"], 0)

class HeavyRainfallAnalysisTests(unittest.TestCase):
    def test_heavy_rainfall_detection(self):
        start = date(2020, 1, 1)
        records = []
        for i in range(60):
            day = start + timedelta(days=i)
            rain = 2.0 if i % 2 == 0 else 0.0
            if i == 15:
                rain = 85.0
            records.append({"date": day.isoformat(), "prcp_mm": rain})
        result = analyze_heavy_rainfall(records, start, start + timedelta(days=59))
        self.assertGreaterEqual(result["threshold"], 25.0)
        self.assertGreaterEqual(result["totalEvents"], 1)
        self.assertIn("yearlyStats", result)
        self.assertEqual(result["events"][0]["peakPrecipitationMm"], 85.0)

class DroughtAnalysisTests(unittest.TestCase):
    def test_drought_consecutive_dry_days_detection(self):
        start = date(2020, 1, 1)
        records = []
        # 20 consecutive dry days (rain = 0.0), then rain
        for i in range(40):
            day = start + timedelta(days=i)
            rain = 0.0 if i < 20 else 10.0
            records.append({"date": day.isoformat(), "prcp_mm": rain})
        result = analyze_drought(records, start, start + timedelta(days=39))
        self.assertEqual(result["totalEvents"], 1)
        self.assertEqual(result["events"][0]["durationDays"], 20)
        self.assertGreaterEqual(result["yearlyStats"][0]["totalDryDays"], 20)

if __name__ == "__main__":
    unittest.main()
