import struct
import threading
import time
import queue
from loguru import logger
from config.settings import CAN_ARBITRATION_IDS


class CANFrame:
    def __init__(self, arbitration_id: int, data: bytes, is_error: bool = False):
        self.arbitration_id = arbitration_id
        self.data = data
        self.is_error = is_error
        self.timestamp = time.time()

    def __repr__(self):
        return (
            f"CANFrame(id=0x{self.arbitration_id:03X}, "
            f"data={self.data.hex()}, error={self.is_error})"
        )


class VirtualCANBus:
    def __init__(self):
        self._tx_queue = queue.Queue(maxsize=256)
        self._rx_queue = queue.Queue(maxsize=256)
        self._running = False
        self._thread = None
        self._traffic_log = []
        self._max_log = 200
        self._lock = threading.Lock()
        self._subscribers = []
        logger.info("VirtualCANBus initialised.")

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._bus_loop, daemon=True)
        self._thread.start()
        logger.info("Virtual CAN bus running.")

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)

    def _bus_loop(self):
        while self._running:
            try:
                frame = self._tx_queue.get(timeout=0.1)
                self._rx_queue.put(frame)
                with self._lock:
                    self._traffic_log.append(frame)
                    if len(self._traffic_log) > self._max_log:
                        self._traffic_log.pop(0)
                for cb in self._subscribers:
                    try:
                        cb(frame)
                    except Exception as exc:
                        logger.error(f"CAN subscriber error: {exc}")
            except queue.Empty:
                continue

    def send(self, frame: CANFrame):
        try:
            self._tx_queue.put_nowait(frame)
        except queue.Full:
            logger.warning("CAN TX queue full, dropping frame.")

    def receive(self, timeout: float = 0.1):
        try:
            return self._rx_queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def subscribe(self, callback):
        self._subscribers.append(callback)

    def get_traffic_log(self, n: int = 50) -> list:
        with self._lock:
            return list(self._traffic_log[-n:])

    @staticmethod
    def encode_rpm(rpm: float) -> bytes:
        return struct.pack(">H", int(rpm))

    @staticmethod
    def encode_temp(temp: float) -> bytes:
        return struct.pack(">h", int(temp * 10))

    @staticmethod
    def encode_pressure(pressure: float) -> bytes:
        return struct.pack(">H", int(pressure))

    @staticmethod
    def encode_voltage(voltage: float) -> bytes:
        return struct.pack(">H", int(voltage * 100))

    @staticmethod
    def encode_throttle(throttle: float) -> bytes:
        return struct.pack(">H", int(throttle * 100))

    @staticmethod
    def decode_rpm(data: bytes) -> float:
        return struct.unpack(">H", data[:2])[0]

    @staticmethod
    def decode_temp(data: bytes) -> float:
        return struct.unpack(">h", data[:2])[0] / 10.0

    @staticmethod
    def decode_pressure(data: bytes) -> float:
        return struct.unpack(">H", data[:2])[0]

    @staticmethod
    def decode_voltage(data: bytes) -> float:
        return struct.unpack(">H", data[:2])[0] / 100.0

    @staticmethod
    def decode_throttle(data: bytes) -> float:
        return struct.unpack(">H", data[:2])[0] / 100.0


class CANTransmitter:
    def __init__(self, bus: VirtualCANBus, ecu):
        self._bus = bus
        self._ecu = ecu
        self._running = False
        self._thread = None
        logger.info("CANTransmitter initialised.")

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._transmit_loop, daemon=True)
        self._thread.start()
        logger.info("CAN transmitter thread started.")

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)

    def _transmit_loop(self):
        while self._running:
            tel = self._ecu.get_telemetry()
            frames = [
                CANFrame(CAN_ARBITRATION_IDS["rpm"], VirtualCANBus.encode_rpm(tel["rpm"])),
                CANFrame(CAN_ARBITRATION_IDS["engine_temp"], VirtualCANBus.encode_temp(tel["engine_temp"])),
                CANFrame(CAN_ARBITRATION_IDS["fuel_pressure"], VirtualCANBus.encode_pressure(tel["fuel_pressure"])),
                CANFrame(CAN_ARBITRATION_IDS["battery_voltage"], VirtualCANBus.encode_voltage(tel["battery_voltage"])),
                CANFrame(CAN_ARBITRATION_IDS["throttle_position"], VirtualCANBus.encode_throttle(tel["throttle_position"])),
            ]
            for frame in frames:
                self._bus.send(frame)
            time.sleep(0.1)

    def send_fault_frame(self, fault_code: int):
        frame = CANFrame(
            CAN_ARBITRATION_IDS["fault_frame"],
            struct.pack(">I", fault_code),
            is_error=True,
        )
        self._bus.send(frame)
        logger.warning(f"Fault CAN frame sent: 0x{fault_code:04X}")

    def send_invalid_frame(self):
        frame = CANFrame(0x7FF, b"\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF", is_error=True)
        self._bus.send(frame)
        logger.warning("Invalid CAN frame injected.")
