import time
import pytest
from diagnostics.dtc_manager import DTC_DEFINITIONS
from diagnostics.uds_handler import SESSION_DEFAULT, SESSION_EXTENDED, SID_READ_DTC, SID_CLEAR_DTC, SID_SESSION_CTRL, SID_READ_DATA, SID_ECU_RESET


class TestDTCManager:
    def test_inject_known_dtc(self, dtc_mgr):
        dtc_mgr.clear_dtcs()
        dtc_mgr.inject_dtc("P0217")
        active = [d["code"] for d in dtc_mgr.get_active_dtcs()]
        assert "P0217" in active

    def test_inject_multiple_dtcs(self, dtc_mgr):
        dtc_mgr.clear_dtcs()
        for code in ["P0217", "P0560", "P0300"]:
            dtc_mgr.inject_dtc(code)
        codes = [d["code"] for d in dtc_mgr.get_active_dtcs()]
        assert set(["P0217", "P0560", "P0300"]).issubset(set(codes))

    def test_clear_dtcs(self, dtc_mgr):
        dtc_mgr.inject_dtc("P0200")
        dtc_mgr.clear_dtcs()
        assert dtc_mgr.get_active_dtcs() == []

    def test_dtc_has_required_fields(self, dtc_mgr):
        dtc_mgr.clear_dtcs()
        dtc_mgr.inject_dtc("P0087")
        dtcs = dtc_mgr.get_active_dtcs()
        for dtc in dtcs:
            assert "code" in dtc
            assert "desc" in dtc
            assert "severity" in dtc

    def test_all_dtc_definitions_have_severity(self):
        for code, info in DTC_DEFINITIONS.items():
            assert "severity" in info
            assert info["severity"] in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]

    def test_overheat_auto_triggers_dtc(self, ecu, dtc_mgr):
        dtc_mgr.clear_dtcs()
        ecu.reset()
        ecu.inject_fault("overheat")
        for _ in range(20):
            time.sleep(0.3)
            tel = ecu.get_telemetry()
            if tel.get("engine_temp", 0) >= 120.0:
                break
        time.sleep(1.5)
        codes = [d["code"] for d in dtc_mgr.get_active_dtcs()]
        ecu.clear_fault("overheat")
        ecu.reset()
        assert "P0217" in codes


class TestUDSHandler:
    def test_session_control_default(self, uds):
        resp = uds.process_request(SID_SESSION_CTRL, {"mode": SESSION_DEFAULT})
        assert resp["status"] == "positive"
        assert resp["session"] == SESSION_DEFAULT

    def test_session_control_extended(self, uds):
        resp = uds.process_request(SID_SESSION_CTRL, {"mode": SESSION_EXTENDED})
        assert resp["status"] == "positive"
        assert resp["session"] == SESSION_EXTENDED

    def test_read_dtc(self, uds, dtc_mgr):
        dtc_mgr.inject_dtc("P0300")
        resp = uds.process_request(SID_READ_DTC)
        assert resp["status"] == "positive"
        assert "dtcs" in resp
        assert isinstance(resp["dtcs"], list)

    def test_clear_dtc(self, uds, dtc_mgr):
        dtc_mgr.inject_dtc("P0200")
        resp = uds.process_request(SID_CLEAR_DTC)
        assert resp["status"] == "positive"

    def test_read_data_vin(self, uds):
        resp = uds.process_request(SID_READ_DATA, {"did": 0xF190})
        assert resp["status"] == "positive"
        assert "RR" in resp["value"]

    def test_read_data_rpm(self, uds):
        resp = uds.process_request(SID_READ_DATA, {"did": 0x0100})
        assert resp["status"] == "positive"
        assert isinstance(resp["value"], (int, float))

    def test_read_data_unknown_did(self, uds):
        resp = uds.process_request(SID_READ_DATA, {"did": 0xFFFF})
        assert resp["status"] == "negative_response"

    def test_ecu_reset(self, uds):
        resp = uds.process_request(SID_ECU_RESET)
        assert resp["status"] == "positive"

    def test_unknown_sid(self, uds):
        resp = uds.process_request(0xFF)
        assert resp["status"] == "negative_response"


class TestOBD2Handler:
    def test_query_rpm(self, obd2):
        resp = obd2.query(0x0C)
        assert resp["status"] == "ok"
        assert resp["name"] == "rpm"

    def test_query_engine_temp(self, obd2):
        resp = obd2.query(0x05)
        assert resp["status"] == "ok"
        assert resp["name"] == "engine_temp"

    def test_query_unknown_pid(self, obd2):
        resp = obd2.query(0xFF)
        assert resp["status"] == "error"
