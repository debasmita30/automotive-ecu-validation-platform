import threading
import time
from loguru import logger
from can_bus.virtual_bus import VirtualCANBus, CANFrame
from config.settings import CAN_ARBITRATION_IDS
from database.db_manager import DatabaseManager


class CANMonitor:
    def __init__(self, bus: VirtualCANBus, db: DatabaseManager):
        self._bus = bus
        self._db = db
        self._decoded_log = []
        self._max_log = 300
        self._lock = threading.Lock()
        bus.subscribe(self._on_frame)
        logger.info("CANMonitor initialised.")

    def _on_frame(self, frame: CANFrame):
        decoded = self._decode(frame)
        with self._lock:
            self._decoded_log.append(decoded)
            if len(self._decoded_log) > self._max_log:
                self._decoded_log.pop(0)
        self._db.insert_can_frame(decoded)

    def _decode(self, frame: CANFrame) -> dict:
        aid = frame.arbitration_id
        ts = frame.timestamp
        raw = frame.data.hex()
        result = {"arbitration_id": f"0x{aid:03X}", "raw": raw, "timestamp": ts, "error": frame.is_error}

        try:
            if aid == CAN_ARBITRATION_IDS["rpm"]:
                result["signal"] = "RPM"
                result["value"] = VirtualCANBus.decode_rpm(frame.data)
                result["unit"] = "rpm"
            elif aid == CAN_ARBITRATION_IDS["engine_temp"]:
                result["signal"] = "Engine Temp"
                result["value"] = VirtualCANBus.decode_temp(frame.data)
                result["unit"] = "°C"
            elif aid == CAN_ARBITRATION_IDS["fuel_pressure"]:
                result["signal"] = "Fuel Pressure"
                result["value"] = VirtualCANBus.decode_pressure(frame.data)
                result["unit"] = "kPa"
            elif aid == CAN_ARBITRATION_IDS["battery_voltage"]:
                result["signal"] = "Battery Voltage"
                result["value"] = VirtualCANBus.decode_voltage(frame.data)
                result["unit"] = "V"
            elif aid == CAN_ARBITRATION_IDS["throttle_position"]:
                result["signal"] = "Throttle"
                result["value"] = VirtualCANBus.decode_throttle(frame.data)
                result["unit"] = "%"
            elif aid == CAN_ARBITRATION_IDS["fault_frame"]:
                result["signal"] = "FAULT"
                result["value"] = int.from_bytes(frame.data[:4], "big")
                result["unit"] = "code"
            else:
                result["signal"] = "UNKNOWN"
                result["value"] = None
                result["unit"] = ""
        except Exception as exc:
            logger.error(f"CAN decode error: {exc}")
            result["signal"] = "DECODE_ERROR"
            result["value"] = None
            result["unit"] = ""

        return result

    def get_log(self, n: int = 50) -> list:
        with self._lock:
            return list(self._decoded_log[-n:])
