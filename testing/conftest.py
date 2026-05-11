import sys
import os
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ecu.simulator import ECUSimulator
from can_bus.virtual_bus import VirtualCANBus, CANTransmitter
from diagnostics.dtc_manager import DTCManager
from diagnostics.uds_handler import UDSHandler, OBD2Handler
from faults.fault_engine import FaultEngine
from database.db_manager import DatabaseManager


@pytest.fixture(scope="session")
def db(tmp_path_factory):
    path = str(tmp_path_factory.mktemp("db") / "test.db")
    return DatabaseManager(db_path=path)


@pytest.fixture(scope="session")
def ecu():
    sim = ECUSimulator()
    sim.start()
    yield sim
    sim.stop()


@pytest.fixture(scope="session")
def can_bus():
    bus = VirtualCANBus()
    bus.start()
    yield bus
    bus.stop()


@pytest.fixture(scope="session")
def transmitter(can_bus, ecu):
    tx = CANTransmitter(can_bus, ecu)
    tx.start()
    yield tx
    tx.stop()


@pytest.fixture(scope="session")
def dtc_mgr(ecu, db):
    mgr = DTCManager(ecu, db)
    mgr.start()
    yield mgr
    mgr.stop()


@pytest.fixture(scope="session")
def uds(ecu, dtc_mgr):
    return UDSHandler(ecu, dtc_mgr)


@pytest.fixture(scope="session")
def obd2(ecu):
    return OBD2Handler(ecu)


@pytest.fixture(scope="session")
def fault_engine(ecu, transmitter, db):
    return FaultEngine(ecu, transmitter, db)
