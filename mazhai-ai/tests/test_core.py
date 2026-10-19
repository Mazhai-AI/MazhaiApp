import os
import tempfile
import unittest
from pathlib import Path

tmp = tempfile.TemporaryDirectory()
os.environ["MAZHAI_DB_PATH"] = str(Path(tmp.name) / "test.db")

from backend.app.districts import DISTRICTS
from backend.app.database.db import init_db, connect
from backend.app.services.weather import district_by_id
from backend.app.main import app
from fastapi.testclient import TestClient

class MazhaiCoreTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        cls.client = TestClient(app)

    def test_all_38_districts_present_and_unique(self):
        self.assertEqual(len(DISTRICTS), 38)
        self.assertEqual(len({d["id"] for d in DISTRICTS}), 38)
        self.assertEqual(len({d["name"] for d in DISTRICTS}), 38)

    def test_coordinates_are_valid(self):
        for d in DISTRICTS:
            self.assertGreaterEqual(d["lat"], 8)
            self.assertLessEqual(d["lat"], 14)
            self.assertGreaterEqual(d["lon"], 76)
            self.assertLessEqual(d["lon"], 81)

    def test_district_lookup(self):
        self.assertEqual(district_by_id("chennai")["name"], "Chennai")
        self.assertIsNone(district_by_id("not-a-district"))

    def test_health_endpoint(self):
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")

    def test_district_directory_endpoint(self):
        response = self.client.get("/api/districts")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 38)

    def test_search_districts(self):
        response = self.client.get("/api/districts?q=chennai")
        self.assertEqual(response.status_code, 200)
        self.assertEqual([d["id"] for d in response.json()["districts"]], ["chennai"])

    def test_unknown_district_returns_404(self):
        response = self.client.get("/api/weather/forecast?district_id=not-a-district")
        self.assertEqual(response.status_code, 404)

    def test_invalid_history_dates_rejected(self):
        response = self.client.get("/api/rainfall/history?district_id=chennai&start=bad&end=2026-01-01")
        self.assertEqual(response.status_code, 400)

    def test_source_registry_is_explicit_about_imd(self):
        response = self.client.get("/api/sources/status")
        self.assertEqual(response.status_code, 200)
        imd = [p for p in response.json()["providers"] if p["name"].startswith("India Meteorological")]
        self.assertEqual(imd[0]["status"], "not_integrated")

    def test_ai_missing_key_is_graceful(self):
        old = os.environ.pop("MISTRAL_API_KEY", None)
        try:
            response = self.client.post("/api/ai/ask", json={"question":"Explain rainfall patterns","district_id":"chennai"})
            self.assertEqual(response.status_code, 200)
            self.assertFalse(response.json()["available"])
        finally:
            if old is not None:
                os.environ["MISTRAL_API_KEY"] = old

if __name__ == "__main__":
    unittest.main()
