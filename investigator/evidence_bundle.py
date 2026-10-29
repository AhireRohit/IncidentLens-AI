
import json
from datetime import datetime
from pathlib import Path

from investigator.sensor_analysis import analyze_sensors
from investigator.event_analysis import analyze_events
from investigator.context_retrieval import retrieve_context


DATA_DIR = Path("data/generated/cooling_failure")
MANUAL_PATH = Path("data/reference/equipment_manual.md")


def build_evidence_bundle(question):

    sensor_path = DATA_DIR / "sensor_readings.csv"
    events_path = DATA_DIR / "events.jsonl"
    maintenance_path = DATA_DIR / "maintenance.csv"

    # Tool 1: Sensor analysis
    sensors = analyze_sensors(sensor_path)

    # Tool 2: Event analysis
    events = analyze_events(events_path, sensor_path)

    # Tool 3: Documentation and maintenance retrieval
    context = retrieve_context(
        MANUAL_PATH,
        maintenance_path,
        events_path,
        machine_id=sensors["machine_id"]
    )

    # Calculate time differences between major events
    def seconds_between(first, second):
        if first is None or second is None:
            return None

        return (
            datetime.fromisoformat(second)
            - datetime.fromisoformat(first)
        ).total_seconds()

    flow_time = sensors["first_low_cooling_flow"]
    warning_time = sensors["first_high_temperature"]
    shutdown_time = sensors["first_shutdown"]

    # Combine all evidence
    bundle = {
        "question": question,
        "machine_id": sensors["machine_id"],

        "sensor_analysis": sensors,

        "event_analysis": events,

        "equipment_manual": context["manual_evidence"],

        "troubleshooting_procedures":
            context["troubleshooting_procedures"],

        "maintenance_history":
            context["maintenance_history"],

        "timing_analysis": {
            "flow_drop_to_warning_seconds":
                seconds_between(flow_time, warning_time),

            "warning_to_shutdown_seconds":
                seconds_between(warning_time, shutdown_time),

            "flow_drop_to_shutdown_seconds":
                seconds_between(flow_time, shutdown_time)
        },

        "investigation_status": "EVIDENCE_COLLECTED",

        "limitations": [
            "Sensor readings and events originate from "
            "the same simulated incident.",
            "No physical inspection confirms the exact "
            "cooling component responsible."
        ]
    }

    return bundle


if __name__ == "__main__":

    question = "Why did conveyor 2 stop around 14:20?"

    bundle = build_evidence_bundle(question)

    output_path = DATA_DIR / "evidence_bundle.json"

    with output_path.open("w", encoding="utf-8") as file:
        json.dump(bundle, file, indent=2)

    print("\n=== AI INCIDENT INVESTIGATOR ===")
    print(f"Question: {bundle['question']}")
    print(f"Machine: {bundle['machine_id']}")

    print(
        f"Sensor readings: "
        f"{bundle['sensor_analysis']['total_readings']}"
    )

    print(
        f"Events: "
        f"{bundle['event_analysis']['total_events']}"
    )

    print(
        f"Manual sections: "
        f"{len(bundle['equipment_manual'])}"
    )

    print(
        f"Maintenance records: "
        f"{len(bundle['maintenance_history'])}"
    )

    print("\nIncident Timing:")
    print(json.dumps(bundle["timing_analysis"], indent=2))

    print(f"\nEvidence saved to: {output_path}")
