
import csv
import json
import random
from datetime import datetime, timedelta
from pathlib import Path

rng = random.Random(123)

START = datetime(2026, 1, 15, 14, 0, 0)
DURATION = 1800

FAULT_SECOND = 14 * 60
TRIP_SECOND = 20 * 60

OUTPUT = Path("data/generated/mechanical_jam")
TRUTH = Path("data/ground_truth/mechanical_jam.json")

OUTPUT.mkdir(parents=True, exist_ok=True)
TRUTH.parent.mkdir(parents=True, exist_ok=True)

temperature = 44.0
ambient = 24.0
running = True

current_warning = False
speed_warning = False

readings = []
events = []


def add_event(timestamp, code, component, message):
    events.append({
        "event_id": f"EVT-{len(events) + 1:03d}",
        "timestamp": timestamp.isoformat(),
        "component": component,
        "event_code": code,
        "message": message
    })


for second in range(DURATION + 1):
    timestamp = START + timedelta(seconds=second)

    # Mechanical resistance increases over six minutes
    progress = min(
        max((second - FAULT_SECOND) / 360, 0.0),
        1.0
    )

    cooling_flow = max(
        0, rng.gauss(12.0, 0.15)
    )

    if running:

        # Higher resistance increases motor load
        current = max(
            0, rng.gauss(8.0 + 8.0 * progress, 0.15)
        )

        # Mechanical resistance slows conveyor movement
        speed = max(
            0, rng.gauss(1.2 - 1.05 * progress, 0.015)
        )

        # Increasing resistance produces vibration
        vibration = max(
            0, rng.gauss(1.1 + 2.5 * progress, 0.05)
        )

        # Motor heats under increasing load
        heating = 0.011 * current

        cooling = (
            0.0044
            * (temperature - ambient)
            * (cooling_flow / 12.0)
        )

        temperature += (
            heating - cooling + rng.gauss(0, 0.012)
        )

        if current >= 12 and not current_warning:
            add_event(
                timestamp,
                "MOTOR_CURRENT_HIGH",
                "conveyor_motor",
                "Motor current exceeded 12 A"
            )
            current_warning = True

        if speed <= 0.6 and not speed_warning:
            add_event(
                timestamp,
                "CONVEYOR_SPEED_LOW",
                "conveyor_motor",
                "Conveyor speed dropped below 0.6 m/s"
            )
            speed_warning = True

        # Simplified controller trip after sustained jam
        if second >= TRIP_SECOND:
            running = False

            current = 0.0
            speed = 0.0
            vibration = 0.15

            add_event(
                timestamp,
                "DRIVE_OVERLOAD_TRIP",
                "controller",
                "Controller stopped conveyor after "
                "sustained excessive load"
            )

    else:
        current = 0.0
        speed = 0.0
        vibration = 0.15

        temperature -= 0.001 * (
            temperature - ambient
        )

    readings.append({
        "timestamp": timestamp.isoformat(),
        "machine_id": "conveyor_2",
        "motor_temp_c": round(temperature, 2),
        "motor_current_a": round(current, 2),
        "conveyor_speed_mps": round(speed, 3),
        "vibration_mm_s": round(vibration, 3),
        "cooling_flow_lpm": round(cooling_flow, 2),
        "controller_state": (
            "RUNNING" if running else "STOPPED"
        )
    })


# Save sensor data
with (OUTPUT / "sensor_readings.csv").open(
    "w", newline="", encoding="utf-8"
) as f:
    writer = csv.DictWriter(
        f, fieldnames=readings[0].keys()
    )
    writer.writeheader()
    writer.writerows(readings)


# Save event logs
with (OUTPUT / "events.jsonl").open(
    "w", encoding="utf-8"
) as f:
    for event in events:
        f.write(json.dumps(event) + "\n")


# Hidden ground truth: never passed to investigator
ground_truth = {
    "scenario": "mechanical_jam",
    "machine_id": "conveyor_2",
    "root_cause": "mechanical_jam",
    "fault_start": (
        START + timedelta(seconds=FAULT_SECOND)
    ).isoformat(),
    "shutdown_time": (
        START + timedelta(seconds=TRIP_SECOND)
    ).isoformat()
}

TRUTH.write_text(
    json.dumps(ground_truth, indent=2),
    encoding="utf-8"
)

print("\n=== MECHANICAL JAM SIMULATION ===")
print(f"Sensor readings: {len(readings)}")
print(f"Events generated: {len(events)}")
print(f"Jam started: {ground_truth['fault_start']}")
print(f"Shutdown: {ground_truth['shutdown_time']}")

for event in events:
    print(
        f"{event['timestamp']} — {event['event_code']}"
    )

print(f"\nDataset saved to: {OUTPUT}")
