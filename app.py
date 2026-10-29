"""IncidentLens — read-only dashboard for AI Incident Investigator.

Works from saved synthetic datasets and checked investigation reports.
No Groq calls, no LLM imports, and no access to ground-truth labels.

Run from repository root: streamlit run app.py
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import altair as alt
import pandas as pd
import streamlit as st


ROOT = Path(__file__).resolve().parent
SCENARIOS_ROOT = ROOT / "data" / "generated"
BENCHMARK_PATH = ROOT / "data" / "evaluation" / "benchmark_summary.json"

METRICS = {
    "motor_temp_c": ("Motor temperature", "°C", [65.0, 75.0]),
    "motor_current_a": ("Motor current", "A", [12.0]),
    "conveyor_speed_mps": ("Conveyor speed", "m/s", [0.6]),
    "vibration_mm_s": ("Vibration", "mm/s", [1.5]),
    "cooling_flow_lpm": ("Cooling flow", "L/min", [2.0]),
}

CATEGORY_NAMES = {
    "cooling_flow_loss": "Cooling-flow loss",
    "mechanical_jam": "Mechanical jam / overload",
    "temperature_sensor_fault": "Temperature sensor malfunction",
    "communication_outage": "Communication outage",
    "no_fault": "No detected fault",
    "unknown": "Undetermined",
}

st.set_page_config(
    page_title="IncidentLens | AI Incident Investigator",
    page_icon="🔎",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
  .stApp { background: radial-gradient(ellipse at 84% 0%, rgba(28,73,101,.15), transparent 38%), #0B1120; }
  section[data-testid="stSidebar"] { background: #101B2E; border-right: 1px solid #273449; }
  [data-testid="stMetric"] { background:#121F32; border:1px solid #26374D; padding:17px 18px; border-radius:12px; }
  [data-testid="stMetricLabel"] { color:#A2B5C9; }
  [data-testid="stMetricValue"] { font-weight:750; color:#F6FAFF; }
  div[data-testid="stExpander"] { border:1px solid #27374D; border-radius:10px; }
  h1, h2, h3 { letter-spacing: -.025em; }
  .eyebrow { color:#64DBD1; font-size:.75rem; letter-spacing:.14em; font-weight:750; }
  .muted { color:#9DB1C6; font-size:.92rem; }
  .notice { padding:12px 16px; border:1px solid #244E62; border-radius:9px; background:#102A3B; }
  .divider-note { color:#88A0B8; font-size:.78rem; }
  .hero-sub { font-size:1.05rem; color:#B2C3D7; margin-top:-.5rem; }
</style>
""",
    unsafe_allow_html=True,
)


def discover_scenarios() -> list[Path]:
    if not SCENARIOS_ROOT.is_dir():
        return []
    return sorted(
        (
            folder
            for folder in SCENARIOS_ROOT.iterdir()
            if folder.is_dir() and (folder / "sensor_readings.csv").is_file()
        ),
        key=lambda folder: (not (folder / "checked_investigation.json").exists(), folder.name),
    )


@st.cache_data(show_spinner=False)
def read_sensors(path: str, modified: float) -> pd.DataFrame:
    df = pd.read_csv(path)
    required = {"timestamp", "controller_state", *METRICS.keys()}
    missing = sorted(required - set(df.columns))
    if missing:
        raise ValueError(f"Sensor CSV is missing columns: {', '.join(missing)}")
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    if df["timestamp"].isna().any():
        raise ValueError("Sensor CSV contains invalid timestamps")
    for field in METRICS:
        df[field] = pd.to_numeric(df[field], errors="coerce")
    df = df.sort_values("timestamp").reset_index(drop=True)
    return df


@st.cache_data(show_spinner=False)
def read_events(path: str, modified: float) -> tuple[list[dict[str, Any]], int]:
    records: list[dict[str, Any]] = []
    invalid = 0
    with Path(path).open(encoding="utf-8-sig") as handle:
        for line in handle:
            if not line.strip():
                continue
            try:
                value = json.loads(line)
                if isinstance(value, dict):
                    records.append(value)
                else:
                    invalid += 1
            except json.JSONDecodeError:
                invalid += 1
    records.sort(key=lambda event: str(event.get("timestamp", "")))
    return records, invalid


@st.cache_data(show_spinner=False)
def read_maintenance(path: str, modified: float) -> pd.DataFrame:
    return pd.read_csv(path)


@st.cache_data(show_spinner=False)
def read_json(path: str, modified: float) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("Expected a JSON object")
    return value


def maybe_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        return read_json(str(path), path.stat().st_mtime)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        st.warning(f"Could not open {path.name}: {exc}")
        return None


def usable_checked_report(blob: dict[str, Any] | None) -> bool:
    if not blob or blob.get("status") != "AUTOMATED_CHECKS_PASSED":
        return False
    if not isinstance(blob.get("report"), dict):
        return False
    verification = blob.get("validation", {})
    return isinstance(verification, dict) and all(
        isinstance(verification.get(name), dict)
        and verification[name].get("passed") is True
        for name in ("sensor_validation", "reference_validation", "maintenance_validation")
    )


def metric_number(value: Any, decimals: int = 2) -> str:
    return f"{float(value):,.{decimals}f}" if pd.notna(value) else "—"


def chart_for_field(df: pd.DataFrame, events: list[dict[str, Any]], field: str, height: int = 230):
    title, unit, thresholds = METRICS[field]
    sample = df[["timestamp", field]].dropna()
    if sample.empty:
        st.info(f"No usable data for {title.lower()}.")
        return
    # Keep charts responsive for larger user-generated datasets.
    if len(sample) > 2500:
        sample = sample.iloc[:: max(1, len(sample) // 2500)]

    y_domain = alt.Y(field + ":Q", title=f"{title} ({unit})", scale=alt.Scale(zero=False))
    chart = (
        alt.Chart(sample)
        .mark_line(color="#56D7CD", strokeWidth=2)
        .encode(
            x=alt.X("timestamp:T", title=None),
            y=y_domain,
            tooltip=[alt.Tooltip("timestamp:T", title="Time"), alt.Tooltip(field + ":Q", format=".3f", title=title)],
        )
    )
    if thresholds:
        boundary = pd.DataFrame({"limit": thresholds})
        chart += alt.Chart(boundary).mark_rule(color="#FFB36E", strokeDash=[5, 5], opacity=.7).encode(
            y=alt.Y("limit:Q"), tooltip=[alt.Tooltip("limit:Q", title="Reference threshold")]
        )
    if events:
        positions = pd.DataFrame(events)
        positions["timestamp"] = pd.to_datetime(positions.get("timestamp"), errors="coerce")
        positions = positions.dropna(subset=["timestamp"])
        if not positions.empty:
            chart += alt.Chart(positions).mark_rule(color="#EF6E82", strokeDash=[2, 4], opacity=.65).encode(
                x="timestamp:T",
                tooltip=[alt.Tooltip("event_code:N", title="Alarm"), alt.Tooltip("timestamp:T", title="Time")],
            )
    st.altair_chart(chart.properties(height=height).interactive(), use_container_width=True)


def show_report_header(report: dict[str, Any] | None, checked: bool) -> None:
    if not checked or report is None:
        st.warning("No validated AI report for this scenario. Telemetry and logs are still available below.")
        st.caption("Generate a validated report locally with: python -m investigator.agent_graph --scenario <case_id>")
        return
    diagnosis = CATEGORY_NAMES.get(report.get("root_cause_category"), str(report.get("root_cause_category", "Unknown")))
    st.success(f"Validated investigation · Leading hypothesis: **{diagnosis}**")
    left, right = st.columns([3, 1])
    with left:
        st.markdown("#### Incident assessment")
        st.write(report.get("incident_summary", "Summary unavailable."))
        st.markdown("**Leading hypothesis**")
        st.write(report.get("leading_hypothesis", "Not provided."))
    with right:
        st.metric("Reported confidence", str(report.get("confidence", "N/A")).capitalize())
        st.metric("Timeline entries", len(report.get("timeline", [])))
    st.caption("A passing validation verifies submitted measurements, reference identifiers and cited maintenance dates; it does not prove the causal hypothesis.")


def list_section(title: str, lines: Any) -> None:
    st.markdown(f"#### {title}")
    if not isinstance(lines, list) or not lines:
        st.caption("Nothing recorded.")
        return
    for line in lines:
        if isinstance(line, str):
            st.markdown(f"- {line}")
        elif isinstance(line, dict):
            st.write(line)


st.sidebar.markdown("### 🔎 IncidentLens")
st.sidebar.caption("AI INCIDENT INVESTIGATOR")
st.sidebar.divider()
folders = discover_scenarios()
if not folders:
    st.markdown("# 🔎 IncidentLens")
    st.info("No sample data found. Add a scenario under `data/generated/<scenario>/sensor_readings.csv` to begin.")
    st.code("python -m simulator.generate\nstreamlit run app.py", language="powershell")
    st.stop()

folder_names = [folder.name for folder in folders]
selected = st.sidebar.selectbox("Scenario", folder_names, index=0, help="Only local synthetic scenario folders are listed.")
folder = SCENARIOS_ROOT / selected

st.sidebar.caption("READ-ONLY DEMO · NO GROQ CALLS")
st.sidebar.markdown("---")
st.sidebar.markdown("**Included artifacts**")
for display, name in (
    ("Sensor telemetry", "sensor_readings.csv"),
    ("Event log", "events.jsonl"),
    ("Maintenance history", "maintenance.csv"),
    ("Validated AI report", "checked_investigation.json"),
):
    mark = "✅" if (folder / name).is_file() else "—"
    st.sidebar.caption(f"{mark} {display}")
st.sidebar.markdown("---")
st.sidebar.caption("Synthetic research prototype. Not a production safety controller.")

try:
    csv_path = folder / "sensor_readings.csv"
    sensors = read_sensors(str(csv_path), csv_path.stat().st_mtime)
except (OSError, ValueError, pd.errors.ParserError) as exc:
    st.error(f"Unable to load sensor data for {selected}: {exc}")
    st.stop()

log_path = folder / "events.jsonl"
try:
    events, invalid_events = read_events(str(log_path), log_path.stat().st_mtime) if log_path.is_file() else ([], 0)
except (OSError, ValueError) as exc:
    st.warning(f"Could not load event log: {exc}")
    events, invalid_events = [], 0

maintenance_path = folder / "maintenance.csv"
try:
    maintenance = read_maintenance(str(maintenance_path), maintenance_path.stat().st_mtime) if maintenance_path.is_file() else pd.DataFrame()
except (OSError, pd.errors.ParserError) as exc:
    st.warning(f"Could not load maintenance history: {exc}")
    maintenance = pd.DataFrame()

saved = maybe_json(folder / "checked_investigation.json")
checked = usable_checked_report(saved)
report = saved["report"] if checked else None

st.markdown('<p class="eyebrow">INDUSTRIAL AI · EVIDENCE-DRIVEN ANALYSIS</p>', unsafe_allow_html=True)
st.title("IncidentLens")
st.markdown('<p class="hero-sub">From machine telemetry to explainable incident investigation.</p>', unsafe_allow_html=True)
st.caption(f"Scenario: `{selected}` · {sensors['timestamp'].min():%d %b %Y, %H:%M:%S} — {sensors['timestamp'].max():%H:%M:%S} · Timestamp timezone not specified")

k1, k2, k3, k4, k5 = st.columns(5)
with k1:
    st.metric("Sensor readings", f"{len(sensors):,}")
with k2:
    st.metric("Logged alarms", len(events))
with k3:
    st.metric("Max motor temp", f"{metric_number(sensors['motor_temp_c'].max())} °C")
with k4:
    st.metric("Minimum flow", f"{metric_number(sensors['cooling_flow_lpm'].min())} L/min")
with k5:
    stop = sensors["controller_state"].astype(str).eq("STOPPED")
    st.metric("Controller status", "Stopped" if stop.iloc[-1] else str(sensors["controller_state"].iloc[-1]).capitalize())

if invalid_events:
    st.warning(f"Ignored {invalid_events} malformed log entries. Interpret event counts with caution.")

st.divider()
overview_tab, telemetry_tab, events_tab, evidence_tab, benchmark_tab = st.tabs([
    "Overview", "Telemetry", "Events & timeline", "Evidence & maintenance", "Benchmark",
])

with overview_tab:
    show_report_header(report, checked)
    st.markdown("#### Operational signals")
    chart_left, chart_right = st.columns(2)
    with chart_left:
        st.caption("Motor temperature · orange dashed lines = reference thresholds")
        chart_for_field(sensors, events, "motor_temp_c", height=260)
    with chart_right:
        st.caption("Cooling flow · red dashed lines = logged alarms")
        chart_for_field(sensors, events, "cooling_flow_lpm", height=260)
    if report:
        with st.expander("Alternative explanations and recommended checks", expanded=False):
            a, b = st.columns(2)
            with a:
                list_section("Alternative explanations", report.get("alternative_explanations"))
            with b:
                list_section("Recommended checks", report.get("recommended_checks"))

with telemetry_tab:
    st.subheader("Telemetry explorer")
    fields = st.multiselect(
        "Sensor channels",
        list(METRICS),
        default=["motor_temp_c", "motor_current_a", "conveyor_speed_mps"],
        format_func=lambda key: METRICS[key][0],
    )
    for field in fields:
        title, unit, _ = METRICS[field]
        st.markdown(f"**{title}**")
        chart_for_field(sensors, events, field, height=230)
    if not fields:
        st.info("Select a channel to view its time series.")
    with st.expander("View telemetry table"):
        st.dataframe(sensors.tail(250), use_container_width=True, hide_index=True)
    st.download_button(
        "Download sensor CSV",
        data=csv_path.read_bytes(),
        file_name=f"{selected}_sensor_readings.csv",
        mime="text/csv",
    )

with events_tab:
    st.subheader("Event timeline")
    if not events:
        st.info("No logged events in this scenario. This does not guarantee that the equipment was fault-free.")
    else:
        for e in events:
            clock = str(e.get("timestamp", "Unknown time"))
            st.markdown(f"**{clock}** · `{e.get('event_code', 'UNKNOWN')}` · {e.get('event_id', '—')}")
            st.caption(f"{e.get('component', 'Unknown component')} — {e.get('message', 'No description')}")
            st.divider()
    if report and isinstance(report.get("timeline"), list):
        st.markdown("#### AI-investigation timeline")
        if report["timeline"]:
            st.dataframe(pd.DataFrame(report["timeline"]), use_container_width=True, hide_index=True)
        else:
            st.caption("No event-specific timeline entries in the validated report.")
    with st.expander("Raw event log"):
        if events:
            st.json(events)
        else:
            st.caption("Empty log.")

with evidence_tab:
    st.subheader("Evidence and verification")
    if checked and saved:
        validation = saved.get("validation", {})
        names = (
            ("Sensor readings", "sensor_validation", "checked_measurements"),
            ("References", "reference_validation", "checked_references"),
            ("Maintenance dates", "maintenance_validation", "checked_date_references"),
        )
        cols = st.columns(3)
        for column, (label, key, counter) in zip(cols, names):
            entry = validation.get(key, {})
            with column:
                st.metric(label, f"{entry.get(counter, 0)} checked", help="Validation of statements the report submitted; it is not comprehensive verification of the narrative.")
        citations = report.get("supporting_evidence", []) if report else []
        st.markdown("#### Cited supporting evidence")
        if citations:
            st.dataframe(pd.DataFrame(citations), use_container_width=True, hide_index=True)
        else:
            st.info("No structured citations. This may be legitimate for a verified normal-operation case.")
        list_section("Missing evidence", report.get("missing_evidence", []))
        st.download_button(
            "Download validated investigation JSON",
            data=json.dumps(saved, ensure_ascii=False, indent=2).encode("utf-8"),
            file_name=f"{selected}_checked_investigation.json",
            mime="application/json",
        )
    else:
        st.warning("This scenario has no saved report with all three validation checks passing.")
    st.markdown("#### Maintenance history")
    if maintenance.empty:
        st.caption("No maintenance data available.")
    else:
        preferred = ["record_id", "timestamp", "component", "maintenance_type", "observation", "status"]
        cols = [c for c in preferred if c in maintenance.columns]
        st.dataframe(maintenance[cols] if cols else maintenance, use_container_width=True, hide_index=True)
    st.info("Reference IDs and maintenance dates are verified against source files. The model's explanation remains a hypothesis, not independently established causation.")

with benchmark_tab:
    st.subheader("Benchmark snapshot")
    stats = maybe_json(BENCHMARK_PATH)
    if not stats:
        st.info("No benchmark summary found. Run `python -m evaluation.benchmark` locally to generate it.")
    else:
        n = int(stats.get("total_incidents", 0))
        validated = int(stats.get("validated_reports", 0))
        columns = st.columns(4)
        with columns[0]:
            st.metric("Generated cases", n)
        with columns[1]:
            st.metric("Validated reports", validated)
        with columns[2]:
            value = stats.get("ai_accuracy_on_validated_reports")
            st.metric("AI accuracy¹", f"{value:.1%}" if isinstance(value, (float, int)) else "N/A")
        with columns[3]:
            value = stats.get("baseline_accuracy")
            st.metric("Rule baseline²", f"{value:.1%}" if isinstance(value, (float, int)) else "N/A")
        st.caption("¹ Among validated completed reports only. ² Across all generated cases. Different denominators; not a head-to-head estimate until every case has been attempted.")
        value = stats.get("ai_end_to_end_success_rate")
        if isinstance(value, (float, int)):
            st.write(f"**AI end-to-end success across generated cases:** {value:.1%}")
        st.info("These are small synthetic development experiments, not independently held-out or real-world deployment results.")

st.divider()
st.caption("IncidentLens · Read-only portfolio demonstration · Simulated conveyor telemetry · No live control of machinery · No API keys required")
