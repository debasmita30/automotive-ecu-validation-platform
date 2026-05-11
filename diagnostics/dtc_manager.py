import time
import threading
from loguru import logger
from config.settings import FAULT_THRESHOLDS
from database.db_manager import DatabaseManager


DTC_DEFINITIONS = {
    "P0217": {"desc": "Engine Coolant Over Temperature Condition", "severity": "CRITICAL"},
    "P0560": {"desc": "System Voltage Malfunction", "severity": "HIGH"},
    "P0300": {"desc": "Random/Multiple Cylinder Misfire Detected", "severity": "HIGH"},
    "P0200": {"desc": "Injector Circuit Malfunction", "severity": "MEDIUM"},
    "P0087": {"desc": "Fuel Rail/System Pressure Too Low", "severity": "HIGH"},
    "P0562": {"desc": "System Voltage Low", "severity": "HIGH"},
    "P0101": {"desc": "Mass Air Flow Sensor Range/Performance", "severity": "MEDIUM"},
    "P0113": {"desc": "Intake Air Temperature Sensor High Input", "severity": "LOW"},
    "U0100": {"desc": "Lost Communication With ECM/PCM", "severity": "CRITICAL"},
    "B0001": {"desc": "CAN Bus Off Error", "severity": "CRITICAL"},
}


class DTCManager:
    def __init__(self, ecu, db: DatabaseManager):
        self._ecu = ecu
        self._db = db
        self._active_dtcs = {}
        self._lock = threading.Lock()
        self._running = False
        self._thread = None
        logger.info("DTCManager initialised.")

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()
        logger.info("DTC monitor thread started.")

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)

    def _monitor_loop(self):
        while self._running:
            self._evaluate(self._ecu.get_telemetry(), self._ecu.get_active_faults())
            time.sleep(0.5)

    def _evaluate(self, tel: dict, faults: list):
        detected = []

        if tel.get("engine_temp", 0) >= FAULT_THRESHOLDS["overheat_temp"]:
            detected.append("P0217")

        if tel.get("battery_voltage", 99) < FAULT_THRESHOLDS["low_voltage"]:
            detected.append("P0560")
            detected.append("P0562")

        if tel.get("fuel_pressure", 999) < FAULT_THRESHOLDS["low_fuel_pressure"]:
            detected.append("P0087")

        if "can_timeout" in faults:
            detected.append("U0100")

        if "sensor_corruption" in faults:
            detected.append("P0101")

        now = time.time()
        with self._lock:
            for code in detected:
                if code not in self._active_dtcs:
                    self._active_dtcs[code] = {
                        "code": code,
                        "desc": DTC_DEFINITIONS[code]["desc"],
                        "severity": DTC_DEFINITIONS[code]["severity"],
                        "first_seen": now,
                        "last_seen": now,
                    }
                    self._db.insert_dtc(code, DTC_DEFINITIONS[code]["desc"], DTC_DEFINITIONS[code]["severity"])
                    logger.warning(f"DTC SET: {code} - {DTC_DEFINITIONS[code]['desc']}")
                else:
                    self._active_dtcs[code]["last_seen"] = now

    def get_active_dtcs(self) -> list:
        with self._lock:
            return list(self._active_dtcs.values())

    def clear_dtcs(self):
        with self._lock:
            count = len(self._active_dtcs)
            self._active_dtcs.clear()
            logger.info(f"Cleared {count} DTC(s).")

    def inject_dtc(self, code: str):
        if code not in DTC_DEFINITIONS:
            logger.error(f"Unknown DTC: {code}")
            return
        now = time.time()
        with self._lock:
            self._active_dtcs[code] = {
                "code": code,
                "desc": DTC_DEFINITIONS[code]["desc"],
                "severity": DTC_DEFINITIONS[code]["severity"],
                "first_seen": now,
                "last_seen": now,
            }
        self._db.insert_dtc(code, DTC_DEFINITIONS[code]["desc"], DTC_DEFINITIONS[code]["severity"])
        logger.warning(f"DTC manually injected: {code}")

    @staticmethod
    def list_all_dtcs() -> dict:
        return DTC_DEFINITIONS
