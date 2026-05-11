import sys
import os
import time
import threading
import argparse

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from loguru import logger

LOG_DIR = os.path.join(os.path.dirname(__file__), "logs")
os.makedirs(LOG_DIR, exist_ok=True)
logger.add(os.path.join(LOG_DIR, "platform_{time}.log"), rotation="10 MB", retention=5, level="DEBUG")

from ecu.simulator import ECUSimulator
from ecu.telemetry import TelemetryCollector
from can_bus.virtual_bus import VirtualCANBus, CANTransmitter
from can_bus.monitor import CANMonitor
from diagnostics.dtc_manager import DTCManager
from diagnostics.uds_handler import UDSHandler
from faults.fault_engine import FaultEngine
from database.db_manager import DatabaseManager
from api.routes import app as fastapi_app, init_app


def build_platform():
    db = DatabaseManager()
    ecu = ECUSimulator()
    bus = VirtualCANBus()
    tx = CANTransmitter(bus, ecu)
    monitor = CANMonitor(bus, db)
    dtc_mgr = DTCManager(ecu, db)
    collector = TelemetryCollector(ecu, db)
    fault_eng = FaultEngine(ecu, tx, db)
    uds = UDSHandler(ecu, dtc_mgr)

    init_app(ecu, dtc_mgr, fault_eng, collector, monitor, uds, db)

    return dict(
        db=db, ecu=ecu, bus=bus, tx=tx, monitor=monitor,
        dtc_mgr=dtc_mgr, collector=collector, fault_eng=fault_eng, uds=uds,
    )


def run_api(platform):
    import uvicorn
    from config.settings import API_HOST, API_PORT
    uvicorn.run(fastapi_app, host=API_HOST, port=API_PORT, log_level="warning")


def run_sil_demo(platform):
    ecu = platform["ecu"]
    fault_eng = platform["fault_eng"]
    dtc_mgr = platform["dtc_mgr"]
    collector = platform["collector"]

    logger.info("=== SIL Demo starting ===")
    ecu.start()
    platform["bus"].start()
    platform["tx"].start()
    dtc_mgr.start()
    collector.start()

    time.sleep(2)
    logger.info("Injecting overheat fault in 3s …")
    time.sleep(3)
    fault_eng.inject("overheat")

    time.sleep(5)
    logger.info("Injecting voltage drop …")
    fault_eng.inject("voltage_drop")

    time.sleep(5)
    logger.info("Active DTCs: %s", [d["code"] for d in dtc_mgr.get_active_dtcs()])

    logger.info("Clearing all faults and resetting ECU …")
    fault_eng.clear_all()
    ecu.reset()

    time.sleep(3)
    logger.info("Final telemetry: %s", collector.get_latest())
    logger.info("=== SIL Demo complete ===")


def main():
    parser = argparse.ArgumentParser(description="ECU Diagnostics Platform")
    parser.add_argument("--mode", choices=["api", "demo", "all"], default="demo")
    args = parser.parse_args()

    logger.info(f"Starting ECU Diagnostics Platform – mode={args.mode}")
    platform = build_platform()

    if args.mode == "api":
        platform["ecu"].start()
        platform["bus"].start()
        platform["tx"].start()
        platform["dtc_mgr"].start()
        platform["collector"].start()
        run_api(platform)

    elif args.mode == "demo":
        run_sil_demo(platform)

    elif args.mode == "all":
        platform["ecu"].start()
        platform["bus"].start()
        platform["tx"].start()
        platform["dtc_mgr"].start()
        platform["collector"].start()
        api_thread = threading.Thread(target=run_api, args=(platform,), daemon=True)
        api_thread.start()
        logger.info("FastAPI running on http://localhost:8000")
        logger.info("Run Streamlit: streamlit run dashboard/app.py")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Shutting down.")


if __name__ == "__main__":
    main()
