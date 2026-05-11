import time
import pytest
from config.settings import (
    RPM_MIN, RPM_MAX, ENGINE_TEMP_MIN, ENGINE_TEMP_MAX,
    FUEL_PRESSURE_MIN, FUEL_PRESSURE_MAX,
    BATTERY_VOLTAGE_MIN, BATTERY_VOLTAGE_MAX,
    THROTTLE_MIN, THROTTLE_MAX,
    FAULT_THRESHOLDS,
)


class TestECUSimulator:
    def test_simulator_starts(self, ecu):
        assert ecu._running is True

    def test_telemetry_returns_dict(self, ecu):
        time.sleep(0.6)
        tel = ecu.get_telemetry()
        assert isinstance(tel, dict)

    def test_telemetry_has_all_keys(self, ecu):
        time.sleep(0.6)
        tel = ecu.get_telemetry()
        for key in ["rpm", "engine_temp", "fuel_pressure", "battery_voltage", "throttle_position", "timestamp"]:
            assert key in tel, f"Missing key: {key}"

    def test_rpm_in_range(self, ecu):
        time.sleep(0.6)
        tel = ecu.get_telemetry()
        assert RPM_MIN <= tel["rpm"] <= RPM_MAX

    def test_engine_temp_in_range(self, ecu):
        time.sleep(0.6)
        tel = ecu.get_telemetry()
        assert ENGINE_TEMP_MIN <= tel["engine_temp"] <= ENGINE_TEMP_MAX + 20

    def test_fuel_pressure_in_range(self, ecu):
        time.sleep(0.6)
        tel = ecu.get_telemetry()
        assert FUEL_PRESSURE_MIN <= tel["fuel_pressure"] <= FUEL_PRESSURE_MAX

    def test_battery_voltage_in_range(self, ecu):
        time.sleep(0.6)
        tel = ecu.get_telemetry()
        assert BATTERY_VOLTAGE_MIN <= tel["battery_voltage"] <= BATTERY_VOLTAGE_MAX

    def test_throttle_in_range(self, ecu):
        time.sleep(0.6)
        tel = ecu.get_telemetry()
        assert THROTTLE_MIN <= tel["throttle_position"] <= THROTTLE_MAX

    def test_overheat_fault_injection(self, ecu):
        ecu.inject_fault("overheat")
        assert "overheat" in ecu.get_active_faults()
        time.sleep(1.5)
        tel = ecu.get_telemetry()
        assert tel["engine_temp"] > 100
        ecu.clear_fault("overheat")

    def test_voltage_drop_fault(self, ecu):
        ecu.inject_fault("voltage_drop")
        assert "voltage_drop" in ecu.get_active_faults()
        time.sleep(2.0)
        tel = ecu.get_telemetry()
        assert tel["battery_voltage"] < 13.5
        ecu.clear_fault("voltage_drop")

    def test_sensor_corruption_fault(self, ecu):
        ecu.inject_fault("sensor_corruption")
        assert "sensor_corruption" in ecu.get_active_faults()
        time.sleep(0.6)
        tel = ecu.get_telemetry()
        assert tel["fuel_pressure"] >= 0
        ecu.clear_fault("sensor_corruption")

    def test_clear_fault(self, ecu):
        ecu.inject_fault("overheat")
        ecu.clear_fault("overheat")
        assert "overheat" not in ecu.get_active_faults()

    def test_reset(self, ecu):
        ecu.inject_fault("overheat")
        ecu.reset()
        assert ecu.get_active_faults() == []
        time.sleep(0.6)
        tel = ecu.get_telemetry()
        assert tel["rpm"] >= RPM_MIN
