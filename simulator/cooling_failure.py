
import csv
import json
import random
from datetime import datetime, timedelta
from pathlib import Path

rng = random.Random(42)

START = datetime(2026, 1, 15, 14, 0, 0)
DURATION = 1800
FAULT_SECOND = 14 * 60

OUTPUT = Path("data/generated/cooling_failure")
TRUTH_OUTPUT = Path("data/ground_truth/cooling_failure.json")

OUTPUT.mkdir(parents=True, exist_ok=True)
TRUTH_OUTPUT.parent.mkdir(parents=True, exist_ok=True)

temperature = 44.0
ambient_temperature = 24.0
running = True
warning_sent = False

readings = []
events = []
shutdown_time = None


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

    # Cooling failure starts at 14:14.
    if second == FAULT_SECOND:
        add_event(
            timestamp,
            "COOLING_FLOW_LOW",
            "cooling_unit",
            "Cooling flow dropped below operating range"
        )

    target_flow = 12.0 if second < FAULT_SECOND else 0.5
    cooling_flow = max(0, rng.gauss(target_flow, 0.05))

    if running:
        current = max(0, rng.gauss(8.0, 0.25))
        speed = max(0, rng.gauss(1.2, 0.02))
        vibration = max(0, rng.gauss(1.1, 0.09))

        heating = 0.011 * current
        cooling = (
            0.0044
            * (temperature - ambient_temperature)
            * (cooling_flow / 12.0)
        )

        temperature += heating - cooling + rng.gauss(0, 0.012)

        if temperature >= 65 and not warning_sent:
            add_event(
                timestamp,
                "MOTOR_TEMP_HIGH",
                "conveyor_motor",
                "Motor temperature exceeded 65 C"
            )
            warning_sent = True

        if temperature >= 75:
            running = False
            shutdown_time = timestamp

            add_event(
                timestamp,
                "THERMAL_SHUTDOWN",
                "controller",
                "Controller stopped conveyor due to overheating"
            )

            current = 0.0
            speed = 0.0
            vibration = 0.15

    else:
        current = 0.0
        speed = 0.0
        vibration = 0.15

        # Simplified passive cooling after shutdown
        temperature -= 0.001 * (
            temperature - ambient_temperature
        )

    readings.append({
        "timestamp": timestamp.isoformat(),
        "machine_id": "conveyor_2",
        "motor_temp_c": round(temperature, 2),
        "motor_current_a": round(current, 2),
        "conveyor_speed_mps": round(speed, 3),
        "vibration_mm_s": round(vibration, 3),
        "cooling_flow_lpm": round(cooling_flow, 2),
        "controller_state": "RUNNING" if running else "STOPPED"
    })


# Save sensor measurements
with (OUTPUT / "sensor_readings.csv").open(
    "w", newline="", encoding="utf-8"
) as file:
    writer = csv.DictWriter(file, fieldnames=readings[0].keys())
    writer.writeheader()
    writer.writerows(readings)


# Save event logs
with (OUTPUT / "events.jsonl").open(
    "w", encoding="utf-8"
) as file:
    for event in events:
        file.write(json.dumps(event) + "\n")


# Ground truth is ONLY for evaluation.
# The AI investigator must never receive this file.
ground_truth = {
    "scenario": "cooling_failure",
    "machine_id": "conveyor_2",
    "root_cause": "cooling_flow_loss",
    "faulty_component": "cooling_unit",
    "fault_start": (
        START + timedelta(seconds=FAULT_SECOND)
    ).isoformat(),
    "shutdown_time": (
        shutdown_time.isoformat()
        if shutdown_time else None
    )
}

with TRUTH_OUTPUT.open("w", encoding="utf-8") as file:
    json.dump(ground_truth, file, indent=2)


print(f"Generated {len(readings)} sensor readings")
print(f"Generated {len(events)} events")
print(f"Fault started: {ground_truth['fault_start']}")
print(f"Shutdown: {ground_truth['shutdown_time']}")
print(f"Sensor data and logs: {OUTPUT}")
