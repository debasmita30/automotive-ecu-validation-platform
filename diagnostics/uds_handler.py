import time
from loguru import logger
from diagnostics.dtc_manager import DTCManager
from ecu.simulator import ECUSimulator

SESSION_DEFAULT = 0x01
SESSION_EXTENDED = 0x03
SESSION_PROGRAMMING = 0x02

SID_READ_DTC = 0x19
SID_CLEAR_DTC = 0x14
SID_READ_DATA = 0x22
SID_SESSION_CTRL = 0x10
SID_ECU_RESET = 0x11


class UDSHandler:
    def __init__(self, ecu: ECUSimulator, dtc_mgr: DTCManager):
        self._ecu = ecu
        self._dtc_mgr = dtc_mgr
        self._session = SESSION_DEFAULT
        logger.info("UDSHandler initialised.")

    def process_request(self, sid: int, params: dict = None) -> dict:
        params = params or {}
        logger.info(f"UDS request SID=0x{sid:02X} session={self._session}")

        if sid == SID_SESSION_CTRL:
            return self._session_control(params.get("mode", SESSION_DEFAULT))
        if sid == SID_READ_DTC:
            return self._read_dtc()
        if sid == SID_CLEAR_DTC:
            return self._clear_dtc()
        if sid == SID_READ_DATA:
            return self._read_data(params.get("did", 0xF190))
        if sid == SID_ECU_RESET:
            return self._ecu_reset()

        return {"status": "negative_response", "nrc": 0x11, "desc": "ServiceNotSupported"}

    def _session_control(self, mode: int) -> dict:
        self._session = mode
        names = {SESSION_DEFAULT: "Default", SESSION_EXTENDED: "Extended", SESSION_PROGRAMMING: "Programming"}
        logger.info(f"UDS session changed to {names.get(mode, 'Unknown')}")
        return {"status": "positive", "session": mode, "desc": names.get(mode, "Unknown")}

    def _read_dtc(self) -> dict:
        dtcs = self._dtc_mgr.get_active_dtcs()
        return {"status": "positive", "dtc_count": len(dtcs), "dtcs": dtcs}

    def _clear_dtc(self) -> dict:
        self._dtc_mgr.clear_dtcs()
        return {"status": "positive", "desc": "DTCs cleared"}

    def _read_data(self, did: int) -> dict:
        tel = self._ecu.get_telemetry()
        did_map = {
            0xF190: {"name": "VIN", "value": "RR-SIL-ECU-2024-001"},
            0x0100: {"name": "RPM", "value": tel["rpm"]},
            0x0101: {"name": "EngineTemp", "value": tel["engine_temp"]},
            0x0102: {"name": "FuelPressure", "value": tel["fuel_pressure"]},
            0x0103: {"name": "BatteryVoltage", "value": tel["battery_voltage"]},
            0x0104: {"name": "ThrottlePosition", "value": tel["throttle_position"]},
        }
        if did in did_map:
            return {"status": "positive", "did": f"0x{did:04X}", **did_map[did]}
        return {"status": "negative_response", "nrc": 0x31, "desc": "RequestOutOfRange"}

    def _ecu_reset(self) -> dict:
        self._ecu.reset()
        self._session = SESSION_DEFAULT
        logger.info("ECU soft reset via UDS.")
        return {"status": "positive", "desc": "ECU reset complete"}


class OBD2Handler:
    PID_MAP = {
        0x0C: "rpm",
        0x05: "engine_temp",
        0x11: "throttle_position",
    }

    def __init__(self, ecu: ECUSimulator):
        self._ecu = ecu
        logger.info("OBD2Handler initialised.")

    def query(self, pid: int) -> dict:
        tel = self._ecu.get_telemetry()
        if pid in self.PID_MAP:
            key = self.PID_MAP[pid]
            return {"status": "ok", "pid": f"0x{pid:02X}", "name": key, "value": tel.get(key)}
        return {"status": "error", "desc": f"PID 0x{pid:02X} not supported"}
