
import sys
import os
import time
import subprocess
import json
import warnings

warnings.filterwarnings("ignore")

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd

from streamlit_autorefresh import st_autorefresh

from ecu.simulator import ECUSimulator
from ecu.telemetry import TelemetryCollector
from can_bus.virtual_bus import VirtualCANBus, CANTransmitter
from can_bus.monitor import CANMonitor
from diagnostics.dtc_manager import DTCManager, DTC_DEFINITIONS
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

html, body, [class*="css"] {
    background-color: #0f172a;
    color: white;
}

.main {
    background: linear-gradient(180deg,#0f172a 0%,#111827 100%);
}

section[data-testid="stSidebar"] {
    background: #111827;
    border-right: 1px solid rgba(255,255,255,0.08);
}

[data-testid="stMetric"] {
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.08);
    padding: 16px;
    border-radius: 14px;
    box-shadow: 0 4px 18px rgba(0,0,0,0.25);
}

[data-testid="stMetricValue"] {
    font-size: 2rem;
    font-weight: 700;
}

.block-container {
    padding-top: 1rem;
    padding-bottom: 2rem;
}

.ecu-card {
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.08);
    padding: 18px;
    border-radius: 16px;
    margin-bottom: 14px;
}

.health-good {
    background: rgba(46,204,113,0.15);
    border-left: 6px solid #2ecc71;
    padding: 14px;
    border-radius: 10px;
}

.health-bad {
    background: rgba(231,76,60,0.15);
    border-left: 6px solid #e74c3c;
    padding: 14px;
    border-radius: 10px;
}

.warning-box {
    background: rgba(243,156,18,0.15);
    border-left: 6px solid #f39c12;
    padding: 14px;
    border-radius: 10px;
}

.stTabs [data-baseweb="tab-list"] {
    gap: 8px;
}

.stTabs [data-baseweb="tab"] {
    background: rgba(255,255,255,0.04);
    border-radius: 8px;
    padding: 10px 18px;
}

</style>
""", unsafe_allow_html=True)

refresh_rate = st.sidebar.slider(
    "Refresh Interval (ms)",
    1000,
    10000,
    2000,
    step=500
)

st_autorefresh(
    interval=refresh_rate,
    key="ecu_dashboard_refresh"
)


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

st.markdown(
    """
    <div style='padding:18px;border-radius:18px;background:linear-gradient(90deg,#1e293b,#0f172a);border:1px solid rgba(255,255,255,0.08);margin-bottom:18px;'>
        <h1 style='margin-bottom:0;'>⚙️ ECU Diagnostics & Validation Platform</h1>
        <p style='font-size:18px;color:#cbd5e1;'>
        Real-Time SIL/HIL Embedded Validation Environment • CAN Diagnostics • Fault Injection • UDS/OBD-II
        </p>
    </div>
    """,
    unsafe_allow_html=True
)

st.sidebar.title("⚙️ ECU Platform")
st.sidebar.markdown("### Rolls-Royce Embedded Validation")

st.sidebar.markdown("---")
st.sidebar.markdown("### ECU Information")
st.sidebar.write("ECU Type: Powertrain Control Module")
st.sidebar.write("Protocol: CAN 2.0B")
st.sidebar.write("Diagnostic Mode: UDS / OBD-II")
st.sidebar.write("Firmware Version: v2.4.1")
st.sidebar.write("Bus Speed: 500 kbps")

mode = st.sidebar.selectbox(
    "Execution Mode",
    ["SIL Simulation", "HIL Ready"]
)

st.sidebar.info(f"Current Mode: {mode}")

page = st.sidebar.radio(
    "Navigation",
    [
        "System Overview",
        "Live Telemetry",
        "CAN Traffic",
        "Diagnostics & DTCs",
        "Fault Injection",
        "Test Runner",
        "Reports & Logs"
    ],
)

telemetry = collector.get_latest()
can_frames = len(monitor.get_log(200))
active_faults = fault_eng.get_active()
active_dtcs = dtc_mgr.get_active_dtcs()

k1, k2, k3, k4 = st.columns(4)

k1.metric("CAN Frames", can_frames)
k2.metric("Active Faults", len(active_faults))
k3.metric("Active DTCs", len(active_dtcs))
k4.metric("System Uptime", f"{int(time.time() % 10000)} s")


if page == "System Overview":

    st.title("📊 Embedded Validation Overview")

    col1, col2, col3 = st.columns(3)

    col1.metric("Telemetry Samples", len(db.fetch_telemetry(limit=1000)))
    col2.metric("Logged DTC Events", len(db.fetch_dtc_history(limit=1000)))
    col3.metric("Executed Tests", len(db.fetch_test_reports(limit=1000)))

    st.markdown("---")

    overview_cols = st.columns(2)

    with overview_cols[0]:
        st.markdown(
            """
            ### Platform Capabilities
            - Real-time ECU simulation
            - CAN diagnostics monitoring
            - Automated fault injection
            - UDS/OBD-II diagnostics
            - SIL/HIL architecture
            - Automated regression testing
            - SQLite telemetry logging
            - Streamlit observability dashboard
            """
        )

    with overview_cols[1]:
        st.markdown(
            """
            ### Engineering Domains
            - Embedded systems
            - ECU validation
            - Automotive diagnostics
            - Functional testing
            - Powertrain simulation
            - CAN communication
            - Reliability engineering
            """
        )


elif page == "Live Telemetry":

    st.title("⚙️ Live ECU Telemetry")

    tel = collector.get_latest()

    if tel:

        st.subheader("Real-Time ECU Health Overview")

        health_cols = st.columns(3)

        with health_cols[0]:
            if tel.get("engine_temp",0) > 115:
                st.markdown('<div class="health-bad">🔥 Engine overheating detected</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="health-good">✅ Thermal system stable</div>', unsafe_allow_html=True)

        with health_cols[1]:
            if tel.get("battery_voltage",0) < 11.8:
                st.markdown('<div class="warning-box">⚠ Low battery voltage</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="health-good">✅ Power rail nominal</div>', unsafe_allow_html=True)

        with health_cols[2]:
            if len(active_dtcs) > 0:
                st.markdown('<div class="health-bad">⚠ Diagnostic events active</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="health-good">✅ No active diagnostic events</div>', unsafe_allow_html=True)

        c1, c2, c3, c4, c5 = st.columns(5)

        c1.metric("RPM", f"{tel.get('rpm', 0):.0f}")
        c2.metric("Engine Temp", f"{tel.get('engine_temp', 0):.1f} °C")
        c3.metric("Fuel Pressure", f"{tel.get('fuel_pressure', 0):.0f} kPa")
        c4.metric("Battery", f"{tel.get('battery_voltage', 0):.2f} V")
        c5.metric("Throttle", f"{tel.get('throttle_position', 0):.1f} %")

        history = collector.get_history(60)

        if len(history) > 1:
            df = pd.DataFrame(history)
            df["time"] = pd.to_datetime(df["timestamp"], unit="s")

            fig = go.Figure()

            fig.add_trace(go.Scatter(
                x=df["time"],
                y=df["rpm"],
                mode="lines",
                name="RPM"
            ))

            fig.add_trace(go.Scatter(
                x=df["time"],
                y=df["engine_temp"],
                mode="lines",
                name="Temp"
            ))

            fig.update_layout(
                height=500,
                template="plotly_dark"
            )

            st.plotly_chart(fig, use_container_width=True)


elif page == "CAN Traffic":

    st.title("🔌 CAN Bus Traffic Monitor")

    frames = monitor.get_log(100)

    if frames:

        df_can = pd.DataFrame(frames)

        df_can["timestamp"] = pd.to_datetime(
            df_can["timestamp"],
            unit="s"
        ).dt.strftime("%H:%M:%S.%f").str[:-3]

        st.dataframe(
            df_can.tail(100).iloc[::-1],
            use_container_width=True,
            hide_index=True,
            height=520,
        )

        st.subheader("CAN Bus Utilization")

        bus_df = pd.DataFrame({
            "Signal": df_can["signal"].value_counts().index,
            "Frames": df_can["signal"].value_counts().values
        })

        fig_bus = px.bar(
            bus_df,
            x="Signal",
            y="Frames",
            text="Frames"
        )

        fig_bus.update_layout(
            height=350,
            template="plotly_dark"
        )

        st.plotly_chart(fig_bus, use_container_width=True)


elif page == "Diagnostics & DTCs":

    st.title("🔍 Diagnostics – DTCs & UDS")

    dtcs = dtc_mgr.get_active_dtcs()

    if dtcs:
        for dtc in dtcs:
            st.error(f"{dtc['code']} - {dtc['desc']}")
    else:
        st.success("No active DTCs")

    if st.button("Clear DTCs"):
        dtc_mgr.clear_dtcs()

    chosen = st.selectbox(
        "Inject DTC",
        list(DTC_DEFINITIONS.keys())
    )

    if st.button("Inject"):
        dtc_mgr.inject_dtc(chosen)


elif page == "Fault Injection":

    st.title("⚡ Fault Injection")

    for name, spec in FAULT_CATALOGUE.items():

        with st.expander(name):

            st.write(spec["desc"])

            c1, c2 = st.columns(2)

            if c1.button(f"Inject {name}"):
                fault_eng.inject(name)

            if c2.button(f"Clear {name}"):
                fault_eng.clear(name)


elif page == "Test Runner":

    st.title("🧪 Automated Test Execution")

    if st.button("Run Full Test Suite"):

        test_dir = os.path.join(os.path.dirname(__file__), "..", "testing")

        cmd = [
            sys.executable,
            "-m",
            "pytest",
            test_dir,
            "-v",
            "--tb=short",
            "--no-header"
        ]

        with st.spinner("Running tests..."):

            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=os.path.join(os.path.dirname(__file__), "..")
            )

        output = result.stdout + result.stderr

        st.code(output)


elif page == "Reports & Logs":

    st.title("📋 Reports & Logs")

    tab1, tab2, tab3 = st.tabs([
        "Telemetry",
        "DTC History",
        "Tests"
    ])

    with tab1:

        rows = db.fetch_telemetry(limit=100)

        if rows:
            st.dataframe(pd.DataFrame(rows), use_container_width=True)

    with tab2:

        rows = db.fetch_dtc_history(limit=100)

        if rows:
            st.dataframe(pd.DataFrame(rows), use_container_width=True)

    with tab3:

        rows = db.fetch_test_reports(limit=100)

        if rows:
            st.dataframe(pd.DataFrame(rows), use_container_width=True)

```
