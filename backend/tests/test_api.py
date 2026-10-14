import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from app.main import app
from app.db import get_cache_stats, get_db_status

class ApiEndpointsTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_root_endpoint(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("message", data)
        self.assertIn("endpoints", data)

    def test_health_endpoint(self):
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "healthy")
        self.assertIn("database", data)
        self.assertIn("cache_stats", data)

    def test_regions_endpoint(self):
        response = self.client.get("/api/regions")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("regions", data)
        self.assertGreaterEqual(len(data["regions"]), 5)
        patna = next((r for r in data["regions"] if "Patna" in r["name"]), None)
        self.assertIsNotNone(patna)
        self.assertIn("latitude", patna)
        self.assertIn("longitude", patna)

    def test_validation_date_order(self):
        # start_date > end_date should return 400
        response = self.client.get("/api/analysis/heatwave?latitude=25.5&longitude=85.1&start_date=2020-01-01&end_date=2010-01-01")
        self.assertEqual(response.status_code, 400)
        self.assertIn("start_date must be on or before end_date", response.json()["detail"])

    def test_validation_latitude_range(self):
        # latitude > 90 should fail FastAPI query validation with 422
        response = self.client.get("/api/analysis/heatwave?latitude=125.5&longitude=85.1&start_date=2010-01-01&end_date=2020-01-01")
        self.assertEqual(response.status_code, 422)

    def test_validation_longitude_range(self):
        # longitude > 180 should fail FastAPI query validation with 422
        response = self.client.get("/api/analysis/heatwave?latitude=25.5&longitude=285.1&start_date=2010-01-01&end_date=2020-01-01")
        self.assertEqual(response.status_code, 422)

    def test_validation_max_range_70_years(self):
        # range > 70 years should return 400
        response = self.client.get("/api/analysis/heatwave?latitude=25.5&longitude=85.1&start_date=1940-01-01&end_date=2022-01-01")
        self.assertEqual(response.status_code, 400)
        self.assertIn("Maximum supported range is 70 years", response.json()["detail"])

    def test_validation_future_date(self):
        # Future date should return 400
        response = self.client.get("/api/analysis/heatwave?latitude=25.5&longitude=85.1&start_date=2020-01-01&end_date=2099-01-01")
        self.assertEqual(response.status_code, 400)

    @patch("app.main.fetch_weather")
    def test_mocked_heatwave_analysis_endpoint(self, mock_fetch):
        # 60 days baseline at 25C and 4 days at 45C keeps 95th percentile around 27C
        from datetime import date, timedelta
        start = date(2015, 5, 1)
        mock_data = []
        for i in range(65):
            day = (start + timedelta(days=i)).isoformat()
            temp = 45.0 if i in (10, 11, 12, 13) else (25.0 + (i % 3))
            mock_data.append({"date": day, "tmax_c": temp, "prcp_mm": 0.0})
        mock_fetch.return_value = mock_data

        end = (start + timedelta(days=64)).isoformat()
        response = self.client.get(f"/api/analysis/heatwave?latitude=25.59&longitude=85.13&start_date=2015-05-01&end_date={end}")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["hazard"], "heatwave")
        self.assertEqual(data["totalEvents"], 1)
        self.assertEqual(data["events"][0]["durationDays"], 4)
        self.assertIn("yearlyStats", data)
        self.assertIn("regression", data)

    @patch("app.main.fetch_weather")
    def test_mocked_rainfall_analysis_endpoint(self, mock_fetch):
        mock_data = []
        for i in range(40):
            day = f"2015-07-{i+1:02d}" if i < 31 else f"2015-08-{i-30:02d}"
            rain = 75.0 if i == 5 else 2.0
            mock_data.append({"date": day, "tmax_c": 32.0, "prcp_mm": rain})
        mock_fetch.return_value = mock_data

        response = self.client.get("/api/analysis/rainfall?latitude=25.59&longitude=85.13&start_date=2015-07-01&end_date=2015-08-09")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["hazard"], "rainfall")
        self.assertGreaterEqual(data["totalEvents"], 1)
        self.assertIn("threshold", data)

    @patch("app.main.fetch_weather")
    def test_mocked_drought_analysis_endpoint(self, mock_fetch):
        mock_data = []
        for i in range(40):
            day = f"2015-01-{i+1:02d}" if i < 31 else f"2015-02-{i-30:02d}"
            rain = 0.0 if i < 20 else 5.0
            mock_data.append({"date": day, "tmax_c": 22.0, "prcp_mm": rain})
        mock_fetch.return_value = mock_data

        response = self.client.get("/api/analysis/drought?latitude=25.59&longitude=85.13&start_date=2015-01-01&end_date=2015-02-09")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["hazard"], "drought")
        self.assertEqual(data["totalEvents"], 1)
        self.assertEqual(data["events"][0]["durationDays"], 20)

    def test_db_status_and_cache_stats(self):
        status = get_db_status()
        self.assertIn(status, ["connected", "memory-cache-fallback", "memory-cache-dev-mode"])
        stats = get_cache_stats()
        self.assertIn("weather_records_count", stats)
        self.assertIn("cached_analyses_count", stats)

    def test_cors_options_preflight_vercel_origin(self):
        origin = "https://climate-hazard-trend-analyzer-silk.vercel.app"
        response = self.client.options(
            "/api/regions",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "content-type",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get("access-control-allow-origin"), origin)
        self.assertIn("GET", response.headers.get("access-control-allow-methods", ""))
        self.assertEqual(response.headers.get("access-control-allow-credentials"), "true")

    def test_cors_get_vercel_origin(self):
        origin = "https://climate-hazard-trend-analyzer-silk.vercel.app"
        response = self.client.get(
            "/api/regions",
            headers={"Origin": origin},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get("access-control-allow-origin"), origin)
        self.assertEqual(response.headers.get("access-control-allow-credentials"), "true")

    def test_cors_disallowed_origin(self):
        origin = "https://unauthorized-domain.example.com"
        response = self.client.options(
            "/api/regions",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "GET",
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.text, "Disallowed CORS origin")

if __name__ == "__main__":
    unittest.main()

