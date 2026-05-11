import time
import math
import random
import threading
from loguru import logger
from diagnostics.dtc_manager import DTCManager
from config.settings import (
    TELEMETRY_DEFAULTS, RPM_MIN, RPM_MAX,
    ENGINE_TEMP_MIN, ENGINE_TEMP_MAX,
    FUEL_PRESSURE_MIN, FUEL_PRESSURE_MAX,
    BATTERY_VOLTAGE_MIN, BATTERY_VOLTAGE_MAX,
    THROTTLE_MIN, THROTTLE_MAX,
    ECU_UPDATE_INTERVAL,
)


class ECUSimulator:
    def __init__(self):
        self._lock = threading.Lock()
        self._running = False
        self._thread = None
        self._tick = 0

        self._dtc_manager = DTCManager()

        self.rpm = float(TELEMETRY_DEFAULTS["rpm"])
        self.engine_temp = float(TELEMETRY_DEFAULTS["engine_temp"])
        self.fuel_pressure = float(TELEMETRY_DEFAULTS["fuel_pressure"])
        self.battery_voltage = float(TELEMETRY_DEFAULTS["battery_voltage"])
        self.throttle_position = float(TELEMETRY_DEFAULTS["throttle_position"])

        self._faults = {
            "overheat": False,
            "voltage_drop": False,
            "sensor_corruption": False,
            "can_timeout": False,
        }

        logger.info("ECUSimulator initialised.")

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        logger.info("ECU simulation thread started.")

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)
        logger.info("ECU simulation thread stopped.")

    def _run_loop(self):
        while self._running:
            self._update()
            time.sleep(ECU_UPDATE_INTERVAL)

    def _update(self):
        with self._lock:
            self._tick += 1
            t = self._tick

            self.throttle_position = round(
                50 + 45 * math.sin(t * 0.05) + random.uniform(-2, 2), 2
            )
            self.throttle_position = max(
                THROTTLE_MIN,
                min(THROTTLE_MAX, self.throttle_position)
            )

            if not self._faults["overheat"]:
                self.rpm = round(
                    800 + (self.throttle_position / 100) * 5500
                    + random.uniform(-80, 80),
                    0
                )

                self.rpm = max(RPM_MIN, min(RPM_MAX, self.rpm))

                self.engine_temp = round(
                    90 + (self.rpm / RPM_MAX) * 25
                    + random.uniform(-1, 1),
                    1
                )

                self.engine_temp = max(
                    ENGINE_TEMP_MIN,
                    min(ENGINE_TEMP_MAX, self.engine_temp)
                )

            else:
                self.engine_temp = round(
                    min(
                        self.engine_temp + random.uniform(0.5, 2.0),
                        135.0
                    ),
                    1
                )

                self.rpm = round(
                    max(
                        self.rpm - random.uniform(50, 150),
                        RPM_MIN
                    ),
                    0
                )

                active_codes = [
                    dtc["code"]
                    for dtc in self._dtc_manager.get_active_dtcs()
                ]

                if "P0217" not in active_codes:
                    self._dtc_manager.inject_dtc("P0217")

            if not self._faults["voltage_drop"]:
                self.battery_voltage = round(
                    12.6 + (self.rpm / RPM_MAX) * 1.8
                    + random.uniform(-0.05, 0.05),
                    2
                )

                self.battery_voltage = max(
                    BATTERY_VOLTAGE_MIN,
                    min(BATTERY_VOLTAGE_MAX, self.battery_voltage)
                )

            else:
                self.battery_voltage = round(
                    max(
                        self.battery_voltage - random.uniform(0.05, 0.2),
                        10.0
                    ),
                    2
                )

            if not self._faults["sensor_corruption"]:
                self.fuel_pressure = round(
                    350 + random.uniform(-30, 30),
                    1
                )

                self.fuel_pressure = max(
                    FUEL_PRESSURE_MIN,
                    min(FUEL_PRESSURE_MAX, self.fuel_pressure)
                )

            else:
                self.fuel_pressure = round(
                    random.uniform(0, 600),
                    1
                )

    def get_telemetry(self) -> dict:
        with self._lock:
            return {
                "rpm": self.rpm,
                "engine_temp": self.engine_temp,
                "fuel_pressure": self.fuel_pressure,
                "battery_voltage": self.battery_voltage,
                "throttle_position": self.throttle_position,
                "timestamp": time.time(),
            }

    def inject_fault(self, fault_name: str):
        with self._lock:
            if fault_name in self._faults:
                self._faults[fault_name] = True
                logger.warning(f"Fault injected: {fault_name}")
            else:
                logger.error(f"Unknown fault: {fault_name}")

    def clear_fault(self, fault_name: str):
        with self._lock:
            if fault_name in self._faults:
                self._faults[fault_name] = False
                logger.info(f"Fault cleared: {fault_name}")

    def get_active_faults(self) -> list:
        with self._lock:
            return [k for k, v in self._faults.items() if v]

    def get_active_dtcs(self):
        return self._dtc_manager.get_active_dtcs()

    def reset(self):
        with self._lock:
            self.rpm = float(TELEMETRY_DEFAULTS["rpm"])
            self.engine_temp = float(TELEMETRY_DEFAULTS["engine_temp"])
            self.fuel_pressure = float(TELEMETRY_DEFAULTS["fuel_pressure"])
            self.battery_voltage = float(TELEMETRY_DEFAULTS["battery_voltage"])
            self.throttle_position = float(TELEMETRY_DEFAULTS["throttle_position"])
            self._faults = {k: False for k in self._faults}
            self._tick = 0

            self._dtc_manager.clear_dtcs()

            logger.info("ECU state reset.")
