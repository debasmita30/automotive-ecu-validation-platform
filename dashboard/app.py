import sys
import os
import time
import subprocess
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd

from ecu.simulator import ECUSimulator
from ecu.telemetry import TelemetryCollector
from can_bus.virtual_bus import VirtualCANBus, CANTransmitter
from can_bus.monitor import CANMonitor
from diagnostics.dtc_manager import DTCManager
from diagnostics.uds_handler import UDSHandler, OBD2Handler
from faults.fault_engine import FaultEngine, FAULT_CATALOGUE
from database.db_manager import DatabaseManager

st.set_page_config(
    page_title="ECU Diagnostics Platform",
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
[data-testid="stMetricValue"] { font-size: 1.6rem; font-weight: 700; }
.fault-card { background: #1e1e2e; border-left: 4px solid #e74c3c; padding: 8px 12px; border-radius: 4px; margin: 4px 0; }
.ok-card   { background: #1e1e2e; border-left: 4px solid #2ecc71; padding: 8px 12px; border-radius: 4px; margin: 4px 0; }
.warn-card { background: #1e1e2e; border-left: 4px solid #f39c12; padding: 8px 12px; border-radius: 4px; margin: 4px 0; }
</style>
""", unsafe_allow_html=True)


@st.cache_resource
def init_platform():
    db = DatabaseManager()
    ecu = ECUSimulator()
    bus = VirtualCANBus()
    tx = CANTransmitter(bus, ecu)
    monitor = CANMonitor(bus, db)
    dtc_mgr = DTCManager(ecu, db)
    collector = TelemetryCollector(ecu, db)
    fault_eng = FaultEngine(ecu, tx, db)
    uds = UDSHandler(ecu, dtc_mgr)

    ecu.start()
    bus.start()
    tx.start()
    dtc_mgr.start()
    collector.start()

    return {
        "ecu": ecu,
        "bus": bus,
        "tx": tx,
        "monitor": monitor,
        "dtc_mgr": dtc_mgr,
        "collector": collector,
        "fault_eng": fault_eng,
        "uds": uds,
        "db": db,
    }


platform = init_platform()
ecu = platform["ecu"]
collector = platform["collector"]
dtc_mgr = platform["dtc_mgr"]
fault_eng = platform["fault_eng"]
monitor = platform["monitor"]
uds = platform["uds"]
db = platform["db"]

st.sidebar.image("https://upload.wikimedia.org/wikipedia/commons/thumb/9/9e/Rolls-Royce_Holdings_logo.svg/320px-Rolls-Royce_Holdings_logo.svg.png", width=200)
st.sidebar.markdown("## ECU Diagnostics Platform")
st.sidebar.markdown("*SIL Simulation – Rolls-Royce Internship*")
st.sidebar.markdown("---")

page = st.sidebar.radio(
    "Navigation",
    ["Live Telemetry", "CAN Traffic", "Diagnostics & DTCs", "Fault Injection", "Test Runner", "Reports & Logs"],
)

auto_refresh = st.sidebar.checkbox("Auto-refresh (2s)", value=True)
if auto_refresh:
    time.sleep(0.05)
    st.rerun() if hasattr(st, "rerun") else st.experimental_rerun()

active_faults = fault_eng.get_active()
active_dtcs = dtc_mgr.get_active_dtcs()
health_ok = len(active_faults) == 0 and len(active_dtcs) == 0

st.sidebar.markdown("---")
if health_ok:
    st.sidebar.success("System Health: OK")
else:
    st.sidebar.error(f"System Health: {len(active_faults)} fault(s), {len(active_dtcs)} DTC(s)")


if page == "Live Telemetry":
    st.title("⚙️ Live ECU Telemetry")
    tel = collector.get_latest()

    if tel:
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("RPM", f"{tel.get('rpm', 0):.0f}", delta=None)
        c2.metric("Engine Temp", f"{tel.get('engine_temp', 0):.1f} °C",
                  delta="⚠ HIGH" if tel.get("engine_temp", 0) > 115 else None,
                  delta_color="inverse")
        c3.metric("Fuel Pressure", f"{tel.get('fuel_pressure', 0):.0f} kPa")
        c4.metric("Battery", f"{tel.get('battery_voltage', 0):.2f} V",
                  delta="⚠ LOW" if tel.get("battery_voltage", 99) < 11.8 else None,
                  delta_color="inverse")
        c5.metric("Throttle", f"{tel.get('throttle_position', 0):.1f} %")

    st.markdown("---")
    history = collector.get_history(120)

    if len(history) > 1:
        df = pd.DataFrame(history)
        df["time"] = pd.to_datetime(df["timestamp"], unit="s")

        col_left, col_right = st.columns(2)

        with col_left:
            fig_rpm = go.Figure()
            fig_rpm.add_trace(go.Scatter(x=df["time"], y=df["rpm"], mode="lines",
                                         line=dict(color="#3498db", width=2), name="RPM"))
            fig_rpm.update_layout(title="Engine RPM", height=280, margin=dict(l=0, r=0, t=30, b=0),
                                   paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                                   font=dict(color="white"))
            fig_rpm.update_xaxes(showgrid=False)
            fig_rpm.update_yaxes(showgrid=True, gridcolor="rgba(255,255,255,0.1)")
            st.plotly_chart(fig_rpm, use_container_width=True)

        with col_right:
            fig_temp = go.Figure()
            fig_temp.add_trace(go.Scatter(x=df["time"], y=df["engine_temp"], mode="lines",
                                           line=dict(color="#e74c3c", width=2), name="Temp °C"))
            fig_temp.add_hline(y=120, line_dash="dash", line_color="orange", annotation_text="Overheat threshold")
            fig_temp.update_layout(title="Engine Temperature", height=280, margin=dict(l=0, r=0, t=30, b=0),
                                    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                                    font=dict(color="white"))
            fig_temp.update_xaxes(showgrid=False)
            fig_temp.update_yaxes(showgrid=True, gridcolor="rgba(255,255,255,0.1)")
            st.plotly_chart(fig_temp, use_container_width=True)

        col_l2, col_r2 = st.columns(2)

        with col_l2:
            fig_v = go.Figure()
            fig_v.add_trace(go.Scatter(x=df["time"], y=df["battery_voltage"], mode="lines",
                                        line=dict(color="#2ecc71", width=2), name="Voltage V"))
            fig_v.add_hline(y=11.5, line_dash="dash", line_color="red", annotation_text="Low voltage")
            fig_v.update_layout(title="Battery Voltage", height=260, margin=dict(l=0, r=0, t=30, b=0),
                                  paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                                  font=dict(color="white"))
            st.plotly_chart(fig_v, use_container_width=True)

        with col_r2:
            fig_fp = go.Figure()
            fig_fp.add_trace(go.Scatter(x=df["time"], y=df["fuel_pressure"], mode="lines",
                                         line=dict(color="#9b59b6", width=2), name="Pressure kPa"))
            fig_fp.add_hline(y=250, line_dash="dash", line_color="orange", annotation_text="Low pressure")
            fig_fp.update_layout(title="Fuel Pressure", height=260, margin=dict(l=0, r=0, t=30, b=0),
                                   paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                                   font=dict(color="white"))
            st.plotly_chart(fig_fp, use_container_width=True)


elif page == "CAN Traffic":
    st.title("🔌 CAN Bus Traffic Monitor")
    frames = monitor.get_log(80)

    if frames:
        df_can = pd.DataFrame(frames)
        df_can["timestamp"] = pd.to_datetime(df_can["timestamp"], unit="s").dt.strftime("%H:%M:%S.%f").str[:-3]
        df_can["error"] = df_can["error"].apply(lambda x: "⚠ ERROR" if x else "OK")
        df_can = df_can[["timestamp", "arbitration_id", "signal", "value", "unit", "error", "raw"]]
        df_can.columns = ["Time", "Arb ID", "Signal", "Value", "Unit", "Status", "Raw"]

        st.dataframe(
            df_can.tail(50).iloc[::-1],
            use_container_width=True,
            height=400,
        )

        st.markdown("---")
        st.subheader("Frame Distribution")
        sig_counts = df_can["Signal"].value_counts().reset_index()
        sig_counts.columns = ["Signal", "Count"]
        fig_pie = px.pie(sig_counts, names="Signal", values="Count", hole=0.4)
        fig_pie.update_layout(height=300, paper_bgcolor="rgba(0,0,0,0)", font=dict(color="white"))
        st.plotly_chart(fig_pie, use_container_width=True)
    else:
        st.info("No CAN frames captured yet. Frames will appear as the ECU runs.")


elif page == "Diagnostics & DTCs":
    st.title("🔍 Diagnostics – DTCs & UDS")

    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("Active Diagnostic Trouble Codes")
        dtcs = dtc_mgr.get_active_dtcs()

        if dtcs:
            severity_color = {"CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡", "LOW": "🟢"}
            for dtc in dtcs:
                sev = dtc.get("severity", "LOW")
                icon = severity_color.get(sev, "⚪")
                st.markdown(
                    f'<div class="fault-card">{icon} <strong>{dtc["code"]}</strong> [{sev}] — {dtc["desc"]}</div>',
                    unsafe_allow_html=True,
                )
        else:
            st.markdown('<div class="ok-card">✅ No active DTCs</div>', unsafe_allow_html=True)

        if st.button("🗑 Clear All DTCs", type="secondary"):
            dtc_mgr.clear_dtcs()
            st.success("DTCs cleared.")

        st.markdown("---")
        st.subheader("Inject DTC Manually")
        from diagnostics.dtc_manager import DTC_DEFINITIONS
        dtc_options = list(DTC_DEFINITIONS.keys())
        chosen = st.selectbox("Select DTC code", dtc_options)
        if st.button("Inject DTC"):
            dtc_mgr.inject_dtc(chosen)
            st.warning(f"DTC {chosen} injected.")

    with col2:
        st.subheader("UDS Request")
        sid_map = {
            "0x10 – Session Control": 0x10,
            "0x19 – Read DTCs": 0x19,
            "0x14 – Clear DTCs": 0x14,
            "0x22 – Read Data": 0x22,
            "0x11 – ECU Reset": 0x11,
        }
        sid_label = st.selectbox("Service ID", list(sid_map.keys()))
        sid = sid_map[sid_label]

        params = {}
        if sid == 0x10:
            mode = st.selectbox("Session Mode", [1, 2, 3])
            params["mode"] = mode
        if sid == 0x22:
            did_options = {"VIN (0xF190)": 0xF190, "RPM (0x0100)": 0x0100,
                           "Temp (0x0101)": 0x0101, "Voltage (0x0103)": 0x0103}
            did_label = st.selectbox("Data ID", list(did_options.keys()))
            params["did"] = did_options[did_label]

        if st.button("Send UDS Request"):
            resp = uds.process_request(sid, params)
            st.json(resp)

        st.markdown("---")
        st.subheader("OBD-II Query")
        obd = OBD2Handler(ecu)
        pid_options = {"RPM (0x0C)": 0x0C, "Engine Temp (0x05)": 0x05, "Throttle (0x11)": 0x11}
        pid_label = st.selectbox("PID", list(pid_options.keys()))
        if st.button("Query OBD-II"):
            result = obd.query(pid_options[pid_label])
            st.json(result)


elif page == "Fault Injection":
    st.title("⚡ Fault Injection Engine")

    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("Available Faults")
        for name, spec in FAULT_CATALOGUE.items():
            with st.expander(f"🔧 {name}"):
                st.write(spec["desc"])
                c_inj, c_clr = st.columns(2)
                if c_inj.button(f"Inject", key=f"inj_{name}"):
                    result = fault_eng.inject(name)
                    st.warning(result.get("desc", "Injected"))
                if c_clr.button(f"Clear", key=f"clr_{name}"):
                    fault_eng.clear(name)
                    st.success(f"{name} cleared")

        st.markdown("---")
        if st.button("🔴 Inject ALL Faults", type="primary"):
            for name in FAULT_CATALOGUE:
                fault_eng.inject(name)
            st.error("All faults injected!")

        if st.button("✅ Clear ALL Faults"):
            fault_eng.clear_all()
            ecu.reset()
            st.success("All faults cleared and ECU reset.")

    with col2:
        st.subheader("Active Faults")
        active = fault_eng.get_active()
        if active:
            for f in active:
                st.markdown(
                    f'<div class="fault-card">🔴 <strong>{f["name"]}</strong> — {f["desc"]}</div>',
                    unsafe_allow_html=True,
                )
        else:
            st.markdown('<div class="ok-card">✅ No active faults</div>', unsafe_allow_html=True)

        st.markdown("---")
        st.subheader("Current Telemetry Under Fault")
        tel = collector.get_latest()
        if tel:
            gauge_data = [
                ("RPM", tel.get("rpm", 0), 0, 7000),
                ("Temp °C", tel.get("engine_temp", 0), 70, 140),
                ("Fuel kPa", tel.get("fuel_pressure", 0), 0, 600),
                ("Voltage V", tel.get("battery_voltage", 0), 9, 15),
            ]
            for label, val, lo, hi in gauge_data:
                fig_g = go.Figure(go.Indicator(
                    mode="gauge+number",
                    value=val,
                    title={"text": label},
                    gauge={
                        "axis": {"range": [lo, hi]},
                        "bar": {"color": "#3498db"},
                        "steps": [
                            {"range": [lo, lo + (hi - lo) * 0.5], "color": "rgba(46,204,113,0.2)"},
                            {"range": [lo + (hi - lo) * 0.5, lo + (hi - lo) * 0.75], "color": "rgba(243,156,18,0.2)"},
                            {"range": [lo + (hi - lo) * 0.75, hi], "color": "rgba(231,76,60,0.2)"},
                        ],
                    },
                ))
                fig_g.update_layout(height=180, margin=dict(l=10, r=10, t=30, b=0),
                                     paper_bgcolor="rgba(0,0,0,0)", font=dict(color="white"))
                st.plotly_chart(fig_g, use_container_width=True)


elif page == "Test Runner":
    st.title("🧪 Automated Test Execution")
    st.markdown("Run the full PyTest suite directly from the dashboard.")

    col1, col2 = st.columns([1, 2])

    with col1:
        test_module = st.selectbox("Test Module", [
            "All Tests",
            "test_ecu",
            "test_can",
            "test_diagnostics",
            "test_faults",
            "test_database",
        ])

        verbose = st.checkbox("Verbose output", value=True)
        run_btn = st.button("▶ Run Tests", type="primary")

    with col2:
        if run_btn:
            test_dir = os.path.join(os.path.dirname(__file__), "..", "testing")
            cmd = [sys.executable, "-m", "pytest"]
            if test_module != "All Tests":
                cmd.append(os.path.join(test_dir, f"{test_module}.py"))
            else:
                cmd.append(test_dir)
            if verbose:
                cmd.append("-v")
            cmd += ["--tb=short", "--no-header"]

            with st.spinner("Running tests..."):
                result = subprocess.run(cmd, capture_output=True, text=True,
                                        cwd=os.path.join(os.path.dirname(__file__), ".."))

            output = result.stdout + result.stderr
            passed = output.count(" PASSED")
            failed = output.count(" FAILED")
            errors = output.count(" ERROR")

            m1, m2, m3 = st.columns(3)
            m1.metric("Passed", passed, delta=None)
            m2.metric("Failed", failed, delta=None)
            m3.metric("Errors", errors, delta=None)

            overall = "PASS" if failed == 0 and errors == 0 else "FAIL"
            if overall == "PASS":
                st.success("All tests passed!")
            else:
                st.error(f"Test run complete: {failed} failed, {errors} errors.")

            st.code(output, language="text")

            db.insert_test_report(
                test_name=test_module,
                result=overall,
                duration=0.0,
                details=f"passed={passed} failed={failed} errors={errors}",
            )
        else:
            st.info("Select a test module and click Run Tests.")


elif page == "Reports & Logs":
    st.title("📋 Reports & Logs")

    tab1, tab2, tab3 = st.tabs(["Telemetry History", "DTC History", "Test Reports"])

    with tab1:
        rows = db.fetch_telemetry(limit=200)
        if rows:
            df = pd.DataFrame(rows)
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="s").dt.strftime("%H:%M:%S")
            st.dataframe(df, use_container_width=True, height=400)
        else:
            st.info("No telemetry data yet.")

    with tab2:
        rows = db.fetch_dtc_history(limit=100)
        if rows:
            df = pd.DataFrame(rows)
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="s").dt.strftime("%Y-%m-%d %H:%M:%S")
            sev_colors = {"CRITICAL": "background-color: #c0392b", "HIGH": "background-color: #e67e22",
                          "MEDIUM": "background-color: #f1c40f", "LOW": "background-color: #27ae60"}
            st.dataframe(df, use_container_width=True, height=400)
        else:
            st.info("No DTC history yet.")

    with tab3:
        rows = db.fetch_test_reports(limit=50)
        if rows:
            df = pd.DataFrame(rows)
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="s").dt.strftime("%Y-%m-%d %H:%M:%S")
            st.dataframe(df, use_container_width=True, height=400)
        else:
            st.info("No test reports yet. Run tests from the Test Runner page.")

    st.markdown("---")
    st.subheader("Log Files")
    log_dir = os.path.join(os.path.dirname(__file__), "..", "logs")
    if os.path.isdir(log_dir):
        log_files = [f for f in os.listdir(log_dir) if f.endswith(".log")]
        if log_files:
            chosen_log = st.selectbox("Select log file", log_files)
            log_path = os.path.join(log_dir, chosen_log)
            with open(log_path, "r") as fh:
                lines = fh.readlines()
            st.text_area("Log contents (last 200 lines)", "".join(lines[-200:]), height=350)
        else:
            st.info("No log files found.")
    else:
        st.info("Logs directory not found.")
