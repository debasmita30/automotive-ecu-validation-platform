import sqlite3
import os
import time
import threading
from loguru import logger
from config.settings import DATABASE_PATH


class DatabaseManager:
    def __init__(self, db_path: str = DATABASE_PATH):
        self._db_path = os.path.abspath(db_path)
        os.makedirs(os.path.dirname(self._db_path), exist_ok=True)
        self._lock = threading.Lock()
        self._init_schema()
        logger.info(f"DatabaseManager ready: {self._db_path}")

    def _get_conn(self):
        return sqlite3.connect(self._db_path, check_same_thread=False)

    def _init_schema(self):
        ddl = """
        CREATE TABLE IF NOT EXISTS telemetry (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp REAL,
            rpm REAL,
            engine_temp REAL,
            fuel_pressure REAL,
            battery_voltage REAL,
            throttle_position REAL
        );
        CREATE TABLE IF NOT EXISTS dtc_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp REAL,
            code TEXT,
            description TEXT,
            severity TEXT
        );
        CREATE TABLE IF NOT EXISTS fault_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp REAL,
            fault_name TEXT,
            description TEXT
        );
        CREATE TABLE IF NOT EXISTS can_frames (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp REAL,
            arbitration_id TEXT,
            signal TEXT,
            value REAL,
            unit TEXT,
            is_error INTEGER
        );
        CREATE TABLE IF NOT EXISTS test_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp REAL,
            test_name TEXT,
            result TEXT,
            duration REAL,
            details TEXT
        );
        """
        with self._lock:
            conn = self._get_conn()
            conn.executescript(ddl)
            conn.commit()
            conn.close()

    def insert_telemetry(self, data: dict):
        sql = """INSERT INTO telemetry
                 (timestamp, rpm, engine_temp, fuel_pressure, battery_voltage, throttle_position)
                 VALUES (?, ?, ?, ?, ?, ?)"""
        with self._lock:
            conn = self._get_conn()
            try:
                conn.execute(sql, (
                    data.get("timestamp", time.time()),
                    data.get("rpm"), data.get("engine_temp"),
                    data.get("fuel_pressure"), data.get("battery_voltage"),
                    data.get("throttle_position"),
                ))
                conn.commit()
            finally:
                conn.close()

    def insert_dtc(self, code: str, desc: str, severity: str):
        sql = "INSERT INTO dtc_history (timestamp, code, description, severity) VALUES (?, ?, ?, ?)"
        with self._lock:
            conn = self._get_conn()
            try:
                conn.execute(sql, (time.time(), code, desc, severity))
                conn.commit()
            finally:
                conn.close()

    def insert_fault(self, fault_name: str, desc: str):
        sql = "INSERT INTO fault_reports (timestamp, fault_name, description) VALUES (?, ?, ?)"
        with self._lock:
            conn = self._get_conn()
            try:
                conn.execute(sql, (time.time(), fault_name, desc))
                conn.commit()
            finally:
                conn.close()

    def insert_can_frame(self, frame: dict):
        sql = """INSERT INTO can_frames
                 (timestamp, arbitration_id, signal, value, unit, is_error)
                 VALUES (?, ?, ?, ?, ?, ?)"""
        with self._lock:
            conn = self._get_conn()
            try:
                conn.execute(sql, (
                    frame.get("timestamp", time.time()),
                    frame.get("arbitration_id", ""),
                    frame.get("signal", ""),
                    frame.get("value"),
                    frame.get("unit", ""),
                    int(frame.get("error", False)),
                ))
                conn.commit()
            finally:
                conn.close()

    def insert_test_report(self, test_name: str, result: str, duration: float, details: str):
        sql = "INSERT INTO test_reports (timestamp, test_name, result, duration, details) VALUES (?, ?, ?, ?, ?)"
        with self._lock:
            conn = self._get_conn()
            try:
                conn.execute(sql, (time.time(), test_name, result, duration, details))
                conn.commit()
            finally:
                conn.close()

    def fetch_telemetry(self, limit: int = 100) -> list:
        sql = "SELECT * FROM telemetry ORDER BY id DESC LIMIT ?"
        with self._lock:
            conn = self._get_conn()
            try:
                rows = conn.execute(sql, (limit,)).fetchall()
                cols = ["id", "timestamp", "rpm", "engine_temp", "fuel_pressure", "battery_voltage", "throttle_position"]
                return [dict(zip(cols, r)) for r in reversed(rows)]
            finally:
                conn.close()

    def fetch_dtc_history(self, limit: int = 50) -> list:
        sql = "SELECT * FROM dtc_history ORDER BY id DESC LIMIT ?"
        with self._lock:
            conn = self._get_conn()
            try:
                rows = conn.execute(sql, (limit,)).fetchall()
                cols = ["id", "timestamp", "code", "description", "severity"]
                return [dict(zip(cols, r)) for r in reversed(rows)]
            finally:
                conn.close()

    def fetch_test_reports(self, limit: int = 50) -> list:
        sql = "SELECT * FROM test_reports ORDER BY id DESC LIMIT ?"
        with self._lock:
            conn = self._get_conn()
            try:
                rows = conn.execute(sql, (limit,)).fetchall()
                cols = ["id", "timestamp", "test_name", "result", "duration", "details"]
                return [dict(zip(cols, r)) for r in reversed(rows)]
            finally:
                conn.close()
