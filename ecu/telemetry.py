import time
import threading
from loguru import logger
from ecu.simulator import ECUSimulator
from database.db_manager import DatabaseManager


class TelemetryCollector:
    def __init__(self, ecu: ECUSimulator, db: DatabaseManager):
        self._ecu = ecu
        self._db = db
        self._running = False
        self._thread = None
        self._history = []
        self._max_history = 500
        self._lock = threading.Lock()
        logger.info("TelemetryCollector initialised.")

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._collect_loop, daemon=True)
        self._thread.start()
        logger.info("Telemetry collection thread started.")

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)

    def _collect_loop(self):
        while self._running:
            data = self._ecu.get_telemetry()
            with self._lock:
                self._history.append(data)
                if len(self._history) > self._max_history:
                    self._history.pop(0)
            self._db.insert_telemetry(data)
            time.sleep(1.0)

    def get_latest(self) -> dict:
        with self._lock:
            if self._history:
                return self._history[-1]
            return {}

    def get_history(self, n: int = 60) -> list:
        with self._lock:
            return list(self._history[-n:])
