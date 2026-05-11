import os

ECU_UPDATE_INTERVAL = 0.5
CAN_INTERFACE = "virtual"
CAN_CHANNEL = "vcan0"
DATABASE_PATH = os.path.join(os.path.dirname(__file__), "..", "database", "ecu_data.db")
LOG_DIR = os.path.join(os.path.dirname(__file__), "..", "logs")
REPORT_DIR = os.path.join(os.path.dirname(__file__), "..", "reports")

TELEMETRY_DEFAULTS = {
    "rpm": 800,
    "engine_temp": 90.0,
    "fuel_pressure": 350.0,
    "battery_voltage": 12.6,
    "throttle_position": 0.0,
}

RPM_MIN = 700
RPM_MAX = 7000
ENGINE_TEMP_MIN = 80.0
ENGINE_TEMP_MAX = 130.0
FUEL_PRESSURE_MIN = 200.0
FUEL_PRESSURE_MAX = 500.0
BATTERY_VOLTAGE_MIN = 11.0
BATTERY_VOLTAGE_MAX = 14.8
THROTTLE_MIN = 0.0
THROTTLE_MAX = 100.0

FAULT_THRESHOLDS = {
    "overheat_temp": 120.0,
    "low_voltage": 11.5,
    "low_fuel_pressure": 250.0,
}

CAN_ARBITRATION_IDS = {
    "rpm": 0x100,
    "engine_temp": 0x101,
    "fuel_pressure": 0x102,
    "battery_voltage": 0x103,
    "throttle_position": 0x104,
    "fault_frame": 0x7DF,
    "dtc_response": 0x7E8,
}

API_HOST = "0.0.0.0"
API_PORT = 8000
