import time
import struct
import pytest
from can_bus.virtual_bus import CANFrame, VirtualCANBus
from config.settings import CAN_ARBITRATION_IDS


class TestVirtualCANBus:
    def test_bus_starts(self, can_bus):
        assert can_bus._running is True

    def test_send_receive_frame(self, can_bus):
        frame = CANFrame(0x100, b"\x01\x02\x03\x04")
        can_bus.send(frame)
        time.sleep(0.1)
        rx = can_bus.receive(timeout=0.5)
        assert rx is not None
        assert rx.arbitration_id == 0x100

    def test_rpm_encoding_decoding(self):
        original = 3500.0
        encoded = VirtualCANBus.encode_rpm(original)
        decoded = VirtualCANBus.decode_rpm(encoded)
        assert decoded == int(original)

    def test_temp_encoding_decoding(self):
        original = 95.5
        encoded = VirtualCANBus.encode_temp(original)
        decoded = VirtualCANBus.decode_temp(encoded)
        assert abs(decoded - original) < 0.2

    def test_pressure_encoding_decoding(self):
        original = 350.0
        encoded = VirtualCANBus.encode_pressure(original)
        decoded = VirtualCANBus.decode_pressure(encoded)
        assert decoded == int(original)

    def test_voltage_encoding_decoding(self):
        original = 12.6
        encoded = VirtualCANBus.encode_voltage(original)
        decoded = VirtualCANBus.decode_voltage(encoded)
        assert abs(decoded - original) < 0.02

    def test_throttle_encoding_decoding(self):
        original = 75.5
        encoded = VirtualCANBus.encode_throttle(original)
        decoded = VirtualCANBus.decode_throttle(encoded)
        assert abs(decoded - original) < 0.02

    def test_fault_frame_injection(self, transmitter):
        transmitter.send_fault_frame(0xE001)
        time.sleep(0.2)
        log = transmitter._bus.get_traffic_log(10)
        assert any(f.arbitration_id == CAN_ARBITRATION_IDS["fault_frame"] for f in log)

    def test_invalid_frame_injection(self, transmitter):
        transmitter.send_invalid_frame()
        time.sleep(0.2)
        log = transmitter._bus.get_traffic_log(10)
        assert any(f.is_error for f in log)

    def test_traffic_log_grows(self, can_bus):
        before = len(can_bus.get_traffic_log(200))
        for i in range(5):
            can_bus.send(CANFrame(0x200 + i, bytes([i, i, i, i])))
        time.sleep(0.3)
        after = len(can_bus.get_traffic_log(200))
        assert after >= before

    def test_subscriber_called(self, can_bus):
        received = []
        can_bus.subscribe(lambda f: received.append(f))
        frame = CANFrame(0x300, b"\xAA\xBB")
        can_bus.send(frame)
        time.sleep(0.3)
        assert len(received) > 0
