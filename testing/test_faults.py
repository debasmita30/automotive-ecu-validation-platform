import time
import pytest
from faults.fault_engine import FAULT_CATALOGUE


class TestFaultEngine:
    def test_inject_overheat(self, fault_engine, ecu):
        ecu.reset()
        result = fault_engine.inject("overheat")
        assert result["status"] == "ok"
        assert "overheat" in ecu.get_active_faults()
        fault_engine.clear("overheat")
        ecu.reset()

    def test_inject_voltage_drop(self, fault_engine, ecu):
        ecu.reset()
        result = fault_engine.inject("voltage_drop")
        assert result["status"] == "ok"
        assert "voltage_drop" in ecu.get_active_faults()
        fault_engine.clear("voltage_drop")
        ecu.reset()

    def test_inject_sensor_corruption(self, fault_engine, ecu):
        ecu.reset()
        result = fault_engine.inject("sensor_corruption")
        assert result["status"] == "ok"
        assert "sensor_corruption" in ecu.get_active_faults()
        fault_engine.clear("sensor_corruption")
        ecu.reset()

    def test_inject_can_timeout(self, fault_engine):
        result = fault_engine.inject("can_timeout")
        assert result["status"] == "ok"
        active = [f["name"] for f in fault_engine.get_active()]
        assert "can_timeout" in active
        fault_engine.clear("can_timeout")

    def test_inject_invalid_can_frame(self, fault_engine):
        result = fault_engine.inject("invalid_can_frame")
        assert result["status"] == "ok"

    def test_inject_comm_failure(self, fault_engine):
        result = fault_engine.inject("comm_failure")
        assert result["status"] == "ok"
        fault_engine.clear("comm_failure")

    def test_inject_unknown_fault(self, fault_engine):
        result = fault_engine.inject("nonexistent_fault")
        assert result["status"] == "error"

    def test_clear_fault(self, fault_engine, ecu):
        ecu.reset()
        fault_engine.inject("overheat")
        fault_engine.clear("overheat")
        assert "overheat" not in ecu.get_active_faults()
        ecu.reset()

    def test_clear_all(self, fault_engine, ecu):
        ecu.reset()
        fault_engine.inject("overheat")
        fault_engine.inject("voltage_drop")
        fault_engine.clear_all()
        assert fault_engine.get_active() == []
        ecu.reset()

    def test_all_catalogue_faults_injectable(self, fault_engine, ecu):
        for name in FAULT_CATALOGUE:
            ecu.reset()
            result = fault_engine.inject(name)
            assert result["status"] == "ok", f"Failed for fault: {name}"
            fault_engine.clear_all()
        ecu.reset()
