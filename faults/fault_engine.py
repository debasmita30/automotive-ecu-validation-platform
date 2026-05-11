import time
import threading
from loguru import logger
from ecu.simulator import ECUSimulator
from can_bus.virtual_bus import CANTransmitter
from database.db_manager import DatabaseManager


FAULT_CATALOGUE = {
    "overheat": {
        "desc": "Engine overheat fault – coolant temperature exceeds limit",
        "ecu_flag": "overheat",
        "can_code": 0xE001,
    },
    "voltage_drop": {
        "desc": "Battery voltage drop – charging system failure",
        "ecu_flag": "voltage_drop",
        "can_code": 0xE002,
    },
    "sensor_corruption": {
        "desc": "Sensor data corruption – ADC noise or wiring fault",
        "ecu_flag": "sensor_corruption",
        "can_code": 0xE003,
    },
    "can_timeout": {
        "desc": "CAN bus timeout – node not responding",
        "ecu_flag": "can_timeout",
        "can_code": 0xE004,
    },
    "invalid_can_frame": {
        "desc": "Invalid CAN frame transmitted – bus error simulation",
        "ecu_flag": None,
        "can_code": None,
    },
    "comm_failure": {
        "desc": "Communication failure – ECU unresponsive",
        "ecu_flag": None,
        "can_code": 0xE005,
    },
}


class FaultEngine:
    def __init__(self, ecu: ECUSimulator, transmitter: CANTransmitter, db: DatabaseManager):
        self._ecu = ecu
        self._tx = transmitter
        self._db = db
        self._active = {}
        self._lock = threading.Lock()
        logger.info("FaultEngine initialised.")

    def inject(self, fault_name: str) -> dict:
        if fault_name not in FAULT_CATALOGUE:
            logger.error(f"Unknown fault: {fault_name}")
            return {"status": "error", "desc": f"Unknown fault: {fault_name}"}

        spec = FAULT_CATALOGUE[fault_name]
        now = time.time()

        with self._lock:
            self._active[fault_name] = {"injected_at": now, **spec}

        if spec["ecu_flag"]:
            self._ecu.inject_fault(spec["ecu_flag"])

        if fault_name == "invalid_can_frame":
            self._tx.send_invalid_frame()
        elif spec["can_code"] is not None:
            self._tx.send_fault_frame(spec["can_code"])

        self._db.insert_fault(fault_name, spec["desc"])
        logger.warning(f"FAULT INJECTED: {fault_name} – {spec['desc']}")
        return {"status": "ok", "fault": fault_name, "desc": spec["desc"]}

    def clear(self, fault_name: str) -> dict:
        if fault_name not in FAULT_CATALOGUE:
            return {"status": "error", "desc": f"Unknown fault: {fault_name}"}

        spec = FAULT_CATALOGUE[fault_name]
        with self._lock:
            self._active.pop(fault_name, None)

        if spec["ecu_flag"]:
            self._ecu.clear_fault(spec["ecu_flag"])

        logger.info(f"Fault cleared: {fault_name}")
        return {"status": "ok", "fault": fault_name, "desc": "cleared"}

    def clear_all(self):
        with self._lock:
            names = list(self._active.keys())
        for name in names:
            self.clear(name)
        logger.info("All faults cleared.")

    def get_active(self) -> list:
        with self._lock:
            return [{"name": k, **v} for k, v in self._active.items()]

    @staticmethod
    def list_faults() -> dict:
        return FAULT_CATALOGUE
