
import json
from datetime import datetime
from pathlib import Path
import pandas as pd
from investigator.sensor_analysis import analyze_sensors


# Match known event codes with sensor-analysis findings

EVENT_SENSOR_MAPPING = {
    # Cooling failure
    "COOLING_FLOW_LOW": "first_low_cooling_flow",
    "MOTOR_TEMP_HIGH": "first_high_temperature",
    "THERMAL_SHUTDOWN": "first_shutdown",

    # Mechanical jam
    "MOTOR_CURRENT_HIGH": "first_high_motor_current",
    "CONVEYOR_SPEED_LOW": "first_low_conveyor_speed",
    "DRIVE_OVERLOAD_TRIP": "first_shutdown",
}



def analyze_events(events_path, sensor_path):
    # Load JSONL event records
    events = []

    with Path(events_path).open(encoding="utf-8") as file:
        for line in file:
            if line.strip():
                events.append(json.loads(line))

    # Sort events chronologically
    events.sort(key=lambda event: event["timestamp"])

    # Retrieve sensor evidence
    sensor_report = analyze_sensors(sensor_path)
    sensor_df = pd.read_csv(sensor_path)
    sensor_rows = sensor_df.set_index("timestamp")

    timeline = []

    for event in events:
        event_time = datetime.fromisoformat(event["timestamp"])
        event_code = event["event_code"]

        # Determine which sensor finding corresponds
        sensor_field = EVENT_SENSOR_MAPPING.get(event_code)

        sensor_timestamp = (
            sensor_report.get(sensor_field)
            if sensor_field else None
        )

        time_difference = None
        timestamp_matches = None

        if sensor_timestamp:
            sensor_time = datetime.fromisoformat(
                sensor_timestamp
            )
            time_difference = (
                event_time - sensor_time
            ).total_seconds()

            timestamp_matches = abs(time_difference) <= 1
        
        # Extrat exact sensor readings at event time
        sensor_snapshot = None
        
        if event["timestamp"] in sensor_rows.index:
            row = sensor_rows.loc[event["timestamp"]]
            
            sensor_snapshot = {
                "motor_temp_c": float(row["motor_temp_c"]),
                "motor_current_a": float(row["motor_current_a"]),
                "conveyor_speed_mps": float(row["conveyor_speed_mps"]),
                "vibration_mm_s": float(row["vibration_mm_s"]),
                "cooling_flow_lpm": float(row["cooling_flow_lpm"]),
                "controller_state": str(row["controller_state"])
            }
                
        timeline.append({
            "event_id": event["event_id"],
            "timestamp": event["timestamp"],
            "component": event["component"],
            "event_code": event_code,
            "message": event["message"],
            "sensor_timestamp": sensor_timestamp,
            "time_difference_seconds": time_difference,
            "timestamp_matches_sensor": timestamp_matches,
            "sensor_snapshot": sensor_snapshot
        })

    # Calculate elapsed time from first logged event
    if timeline:
        first_time = datetime.fromisoformat(
            timeline[0]["timestamp"]
        )

        for event in timeline:
            current_time = datetime.fromisoformat(
                event["timestamp"]
            )
            event["seconds_since_first_event"] = (
                current_time - first_time
            ).total_seconds()

    return {
        "total_events": len(events),
        "timeline": timeline,
    }


if __name__ == "__main__":
    result = analyze_events(
        "data/generated/cooling_failure/events.jsonl",
        "data/generated/cooling_failure/sensor_readings.csv",
    )

    print(json.dumps(result, indent=2))
