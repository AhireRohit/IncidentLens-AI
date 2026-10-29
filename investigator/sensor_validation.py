
import csv
import json
import math
from pathlib import Path


def validate_sensor_claims(claims, events_path, sensor_path):
    """
    Validate structured sensor claims against original
    event logs and sensor CSV readings.
    """

    # Load event logs
    with Path(events_path).open(encoding="utf-8") as file:
        events = {
            event["event_id"]: event
            for line in file
            if line.strip()
            for event in [json.loads(line)]
        }

    # Load original sensor readings
    with Path(sensor_path).open(
        newline="", encoding="utf-8-sig"
    ) as file:
        reader = csv.DictReader(file)
        sensors = {
            row["timestamp"]: row
            for row in reader
        }

    errors = []
    checked = 0

    allowed_fields = {
        "motor_temp_c",
        "motor_current_a",
        "conveyor_speed_mps",
        "vibration_mm_s",
        "cooling_flow_lpm"
    }
    
    # Verify healthy operation independently when there
    # are no logged events and no event-specific claims.
    if not events and not claims:

        if not sensors:
            errors.append("No sensor readings available")

        for timestamp, row in sensors.items():
            try:
                temp = float(row["motor_temp_c"])
                current = float(row["motor_current_a"])
                speed = float(row["conveyor_speed_mps"])
                vibration = float(row["vibration_mm_s"])
                flow = float(row["cooling_flow_lpm"])
                state = row["controller_state"]

            except (ValueError, TypeError, KeyError) as exc:
                errors.append(
                    f"{timestamp}: Invalid sensor data: {exc}"
                )
                continue

            values = [temp, current, speed, vibration, flow]

            if not all(math.isfinite(x) for x in values):
                errors.append(
                    f"{timestamp}: Non-finite sensor reading"
                )
                continue

            # Five sensor readings + controller state
            checked += 6

            if state != "RUNNING":
                errors.append(
                    f"{timestamp}: Controller is {state}, not RUNNING"
                )

            if flow < 2:
                errors.append(
                    f"{timestamp}: Low cooling flow ({flow} L/min)"
                )

            if temp >= 65:
                errors.append(
                    f"{timestamp}: High motor temperature ({temp} C)"
                )

            if current < 0 or current >= 12:
                errors.append(
                    f"{timestamp}: Abnormal motor current ({current} A)"
                )

            if speed <= 0.6:
                errors.append(
                    f"{timestamp}: Low conveyor speed ({speed} m/s)"
                )

            if vibration < 0 or vibration > 1.5:
                errors.append(
                    f"{timestamp}: Abnormal vibration ({vibration} mm/s)"
                )

        return {
            "checked_measurements": checked,
            "errors": errors,
            "passed": checked > 0 and not errors
        }

    for claim in claims:
        event_id = claim["event_id"]
        timestamp = claim["timestamp"]

        # Check that event ID exists
        if event_id not in events:
            errors.append(f"Unknown event ID: {event_id}")
            continue

        actual_event = events[event_id]

        # Check timestamp
        if timestamp != actual_event["timestamp"]:
            errors.append(
                f"{event_id}: Incorrect timestamp "
                f"{timestamp}; expected "
                f"{actual_event['timestamp']}"
            )
            continue

        # Locate actual sensor reading
        if timestamp not in sensors:
            errors.append(
                f"{event_id}: No sensor reading at {timestamp}"
            )
            continue

        actual_row = sensors[timestamp]

        for field, claimed_value in claim["sensor_values"].items():
            # Validate controller state separately
            if field == "controller_state":
                checked += 1
                actual_value = actual_row["controller_state"]

                if claimed_value != actual_value:
                    errors.append(
                        f"{event_id}: controller_state claimed "
                        f"{claimed_value}, actual {actual_value}"
                    )

                continue

            if field not in allowed_fields:
                errors.append(
                    f"{event_id}: Unsupported field {field}"
                )
                continue

            checked += 1

            actual_value = float(actual_row[field])

            if (
                not isinstance(claimed_value, (int, float))
                or not math.isfinite(claimed_value)
                or not math.isclose(
                    float(claimed_value),
                    actual_value,
                    abs_tol=0.001,
                    rel_tol=0
                )
            ):
                errors.append(
                    f"{event_id}: {field} claimed "
                    f"{claimed_value}, actual {actual_value}"
                )

    return {
        "checked_measurements": checked,
        "errors": errors,
        "passed": checked > 0 and len(errors) == 0
    }


if __name__ == "__main__":

    data_dir = Path("data/generated/cooling_failure")

    # Example claims based on the AI investigation
    claims = [
        {
            "event_id": "EVT-001",
            "timestamp": "2026-01-15T14:14:00",
            "sensor_values": {
                "cooling_flow_lpm": 0.45,
                "motor_temp_c": 43.93
            }
        },
        {
            "event_id": "EVT-002",
            "timestamp": "2026-01-15T14:18:17",
            "sensor_values": {
                "motor_temp_c": 65.08,
                "cooling_flow_lpm": 0.56
            }
        },
        {
            "event_id": "EVT-003",
            "timestamp": "2026-01-15T14:20:22",
            "sensor_values": {
                "motor_temp_c": 75.02,
                "motor_current_a": 0.0
            }
        }
    ]

    events_path = data_dir / "events.jsonl"
    sensor_path = data_dir / "sensor_readings.csv"

    print("\n=== TEST 1: CORRECT MEASUREMENTS ===")

    result = validate_sensor_claims(
        claims, events_path, sensor_path
    )

    print(json.dumps(result, indent=2))

    # Deliberately introduce an incorrect reading
    claims[1]["sensor_values"]["motor_temp_c"] = 70.17

    print("\n=== TEST 2: INCORRECT MEASUREMENT ===")

    result = validate_sensor_claims(
        claims, events_path, sensor_path
    )

    print(json.dumps(result, indent=2))
