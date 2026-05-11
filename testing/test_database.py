import time
import pytest


class TestDatabaseManager:
    def test_insert_and_fetch_telemetry(self, db):
        data = {
            "timestamp": time.time(),
            "rpm": 3000,
            "engine_temp": 95.0,
            "fuel_pressure": 350.0,
            "battery_voltage": 12.8,
            "throttle_position": 45.0,
        }
        db.insert_telemetry(data)
        rows = db.fetch_telemetry(limit=10)
        assert len(rows) > 0
        last = rows[-1]
        assert abs(last["rpm"] - 3000) < 1

    def test_insert_and_fetch_dtc(self, db):
        db.insert_dtc("P0300", "Random Misfire", "HIGH")
        rows = db.fetch_dtc_history(limit=10)
        codes = [r["code"] for r in rows]
        assert "P0300" in codes

    def test_insert_test_report(self, db):
        db.insert_test_report("test_voltage", "PASS", 0.12, "Voltage within range")
        rows = db.fetch_test_reports(limit=10)
        names = [r["test_name"] for r in rows]
        assert "test_voltage" in names

    def test_fetch_telemetry_limit(self, db):
        for i in range(5):
            db.insert_telemetry({
                "timestamp": time.time(),
                "rpm": 1000 + i * 100,
                "engine_temp": 90.0,
                "fuel_pressure": 350.0,
                "battery_voltage": 12.6,
                "throttle_position": 20.0,
            })
        rows = db.fetch_telemetry(limit=3)
        assert len(rows) <= 3
