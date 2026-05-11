from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from loguru import logger

app = FastAPI(
    title="ECU Diagnostics API",
    version="1.0.0",
    description="Rolls-Royce SIL ECU Diagnostics & Validation Platform",
)

_ecu = None
_dtc_mgr = None
_fault_engine = None
_telemetry_collector = None
_can_monitor = None
_uds = None
_db = None


def init_app(ecu, dtc_mgr, fault_engine, telemetry_collector, can_monitor, uds, db):
    global _ecu, _dtc_mgr, _fault_engine, _telemetry_collector, _can_monitor, _uds, _db
    _ecu = ecu
    _dtc_mgr = dtc_mgr
    _fault_engine = fault_engine
    _telemetry_collector = telemetry_collector
    _can_monitor = can_monitor
    _uds = uds
    _db = db
    logger.info("FastAPI routes initialised.")


class FaultRequest(BaseModel):
    fault_name: str


class DTCRequest(BaseModel):
    code: str


class UDSRequest(BaseModel):
    sid: int
    params: dict = {}


@app.get("/health")
def health():
    return {"status": "ok", "service": "ECU Diagnostics Platform"}


@app.get("/telemetry/live")
def telemetry_live():
    if _telemetry_collector is None:
        raise HTTPException(503, "Platform not initialised")
    return _telemetry_collector.get_latest()


@app.get("/telemetry/history")
def telemetry_history(n: int = 60):
    if _telemetry_collector is None:
        raise HTTPException(503, "Platform not initialised")
    return _telemetry_collector.get_history(n)


@app.get("/diagnostics/dtcs")
def get_dtcs():
    if _dtc_mgr is None:
        raise HTTPException(503, "Platform not initialised")
    return {"dtcs": _dtc_mgr.get_active_dtcs()}


@app.delete("/diagnostics/dtcs")
def clear_dtcs():
    if _dtc_mgr is None:
        raise HTTPException(503, "Platform not initialised")
    _dtc_mgr.clear_dtcs()
    return {"status": "cleared"}


@app.post("/diagnostics/dtc/inject")
def inject_dtc(req: DTCRequest):
    if _dtc_mgr is None:
        raise HTTPException(503, "Platform not initialised")
    _dtc_mgr.inject_dtc(req.code)
    return {"status": "injected", "code": req.code}


@app.post("/diagnostics/uds")
def uds_request(req: UDSRequest):
    if _uds is None:
        raise HTTPException(503, "Platform not initialised")
    return _uds.process_request(req.sid, req.params)


@app.get("/faults/active")
def get_active_faults():
    if _fault_engine is None:
        raise HTTPException(503, "Platform not initialised")
    return {"faults": _fault_engine.get_active()}


@app.get("/faults/catalogue")
def fault_catalogue():
    from faults.fault_engine import FAULT_CATALOGUE
    return FAULT_CATALOGUE


@app.post("/faults/inject")
def inject_fault(req: FaultRequest):
    if _fault_engine is None:
        raise HTTPException(503, "Platform not initialised")
    result = _fault_engine.inject(req.fault_name)
    if result["status"] == "error":
        raise HTTPException(400, result["desc"])
    return result


@app.post("/faults/clear")
def clear_fault(req: FaultRequest):
    if _fault_engine is None:
        raise HTTPException(503, "Platform not initialised")
    return _fault_engine.clear(req.fault_name)


@app.delete("/faults")
def clear_all_faults():
    if _fault_engine is None:
        raise HTTPException(503, "Platform not initialised")
    _fault_engine.clear_all()
    return {"status": "all faults cleared"}


@app.get("/can/traffic")
def can_traffic(n: int = 50):
    if _can_monitor is None:
        raise HTTPException(503, "Platform not initialised")
    return {"frames": _can_monitor.get_log(n)}


@app.get("/reports/telemetry")
def report_telemetry(limit: int = 100):
    if _db is None:
        raise HTTPException(503, "Platform not initialised")
    return _db.fetch_telemetry(limit)


@app.get("/reports/dtc")
def report_dtc(limit: int = 50):
    if _db is None:
        raise HTTPException(503, "Platform not initialised")
    return _db.fetch_dtc_history(limit)


@app.get("/reports/tests")
def report_tests(limit: int = 50):
    if _db is None:
        raise HTTPException(503, "Platform not initialised")
    return _db.fetch_test_reports(limit)
