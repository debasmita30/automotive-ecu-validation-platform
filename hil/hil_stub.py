"""
HIL (Hardware-in-the-Loop) stub module.

This module provides the interface stubs that allow real embedded hardware
(ESP32 / STM32) to be connected to the ECU Diagnostics Platform.

TO CONNECT REAL HARDWARE:
--------------------------
1. ESP32 via UART/USB:
   - Flash MicroPython or Arduino firmware on the ESP32.
   - Wire UART TX/RX to the host machine via USB-UART bridge (CP2102, CH340).
   - Replace `ESP32HILStub.read_telemetry()` with real `serial.Serial.readline()` parsing.
   - Example: `pip install pyserial` then `serial.Serial('/dev/ttyUSB0', 115200)`

2. STM32 via USB CDC or CAN:
   - Flash STM32 with a CAN-to-USB bridge firmware (e.g. using STM32CubeIDE + bxCAN).
   - Use `python-can` with `interface='slcan'` and `channel='/dev/ttyACM0'`.
   - Replace `VirtualCANBus` with a real `can.interface.Bus` instance.

3. CAN Hardware (PEAK PCAN, Kvaser):
   - Install vendor drivers.
   - Change `CAN_INTERFACE` in config/settings.py to 'pcan' or 'kvaser'.
   - python-can will handle the rest automatically.

These stubs are drop-in replacements — swap in the real implementation when hardware is available.
"""

import time
from loguru import logger


class ESP32HILStub:
    """
    Stub for an ESP32 node sending sensor telemetry over UART.
    Replace `_read_serial` with real pyserial reads when hardware is connected.
    """

    def __init__(self, port: str = "/dev/ttyUSB0", baud: int = 115200):
        self._port = port
        self._baud = baud
        self._connected = False
        logger.info(f"ESP32HILStub created (port={port}, baud={baud}) [STUB MODE]")

    def connect(self):
        # In real use: self._serial = serial.Serial(self._port, self._baud, timeout=1)
        self._connected = True
        logger.info("ESP32HILStub: connect() called [STUB — no real hardware]")

    def disconnect(self):
        self._connected = False
        logger.info("ESP32HILStub: disconnect() called [STUB]")

    def read_telemetry(self) -> dict:
        # In real use: parse JSON line from self._serial.readline()
        logger.debug("ESP32HILStub: read_telemetry() returning stub data")
        return {
            "rpm": 2500.0,
            "engine_temp": 92.0,
            "fuel_pressure": 345.0,
            "battery_voltage": 13.1,
            "throttle_position": 35.0,
            "timestamp": time.time(),
            "source": "ESP32_STUB",
        }

    def send_command(self, command: str):
        # In real use: self._serial.write(command.encode() + b'\n')
        logger.info(f"ESP32HILStub: send_command({command!r}) [STUB]")


class STM32HILStub:
    """
    Stub for an STM32 node connected over CAN-to-USB (slcan) bridge.
    Replace internals with python-can Bus when hardware is available.
    """

    def __init__(self, channel: str = "/dev/ttyACM0"):
        self._channel = channel
        self._bus = None
        logger.info(f"STM32HILStub created (channel={channel}) [STUB MODE]")

    def connect(self):
        # In real use:
        # import can
        # self._bus = can.interface.Bus(bustype='slcan', channel=self._channel, bitrate=500000)
        logger.info("STM32HILStub: connect() called [STUB — no real hardware]")

    def disconnect(self):
        if self._bus:
            self._bus.shutdown()
        logger.info("STM32HILStub: disconnect() called [STUB]")

    def read_can_frame(self):
        # In real use: return self._bus.recv(timeout=1.0)
        logger.debug("STM32HILStub: read_can_frame() [STUB]")
        return None

    def send_can_frame(self, arbitration_id: int, data: bytes):
        # In real use:
        # import can
        # msg = can.Message(arbitration_id=arbitration_id, data=data, is_extended_id=False)
        # self._bus.send(msg)
        logger.info(f"STM32HILStub: send_can_frame(id=0x{arbitration_id:03X}) [STUB]")


class HILManager:
    """
    Aggregates all HIL hardware stubs and provides a unified interface.
    When real hardware is connected, inject real implementations here.
    """

    def __init__(self):
        self._esp32 = ESP32HILStub()
        self._stm32 = STM32HILStub()
        self._active = False
        logger.info("HILManager initialised [STUB MODE]")

    def activate(self):
        self._esp32.connect()
        self._stm32.connect()
        self._active = True
        logger.info("HIL hardware activated [STUB]")

    def deactivate(self):
        self._esp32.disconnect()
        self._stm32.disconnect()
        self._active = False

    def get_esp32_telemetry(self) -> dict:
        return self._esp32.read_telemetry()

    def is_active(self) -> bool:
        return self._active
