
import csv
import json
import random
import shutil
from pathlib import Path


CASE_ID = "case_0202"
SOURCE = Path("data/generated/normal/sensor_readings.csv")
OUTPUT = Path("data/generated") / CASE_ID
TRUTH = Path("data/ground_truth") / f"{CASE_ID}.json"

rng = random.Random(202)

if OUTPUT.exists() or TRUTH.exists():
    raise FileExistsError(
        f"{CASE_ID} already exists. Existing data protected."
    )

with SOURCE.open(newline="", encoding="utf-8-sig") as f:
    readings = list(csv.DictReader(f))

if len(readings) != 1801:
    raise ValueError("Expected 1801 normal sensor readings")

# Inject two short false-temperature excursions.
spike_windows = [
    (12 * 60, 12 * 60 + 12),
    (17 * 60, 17 * 60 + 10)
]

events = []

for second, row in enumerate(readings):

    for start, end in spike_windows:
        if start <= second < end:

            # Only the measured temperature changes.
            # The motor, cooling and controller stay normal.
            false_temperature = rng.gauss(69.0, 0.45)

            row["motor_temp_c"] = round(
                false_temperature, 2
            )

            # Log first high-temperature alarm.
            if second == spike_windows[0][0]:
                events.append({
                    "event_id": "EVT-001",
                    "timestamp": row["timestamp"],
                    "component": "temperature_sensor",
                    "event_code": "MOTOR_TEMP_HIGH",
                    "message": (
                        "Reported motor temperature exceeded 65 C"
                    )
                })

            break

OUTPUT.mkdir(parents=True, exist_ok=False)
TRUTH.parent.mkdir(parents=True, exist_ok=True)

with (OUTPUT / "sensor_readings.csv").open(
    "w", newline="", encoding="utf-8"
) as f:
    writer = csv.DictWriter(
        f, fieldnames=readings[0].keys()
    )
    writer.writeheader()
    writer.writerows(readings)

with (OUTPUT / "events.jsonl").open(
    "w", encoding="utf-8"
) as f:
    for event in events:
        f.write(json.dumps(event) + "\n")

shutil.copyfile(
    "data/generated/cooling_failure/maintenance.csv",
    OUTPUT / "maintenance.csv"
)

truth = {
    "scenario": CASE_ID,
    "machine_id": "conveyor_2",
    "root_cause": "temperature_sensor_fault",
    "fault_type": "intermittent_false_high_reading",
    "fault_start": readings[spike_windows[0][0]]["timestamp"],
    "shutdown_time": None,
    "seed": 202
}

TRUTH.write_text(
    json.dumps(truth, indent=2),
    encoding="utf-8"
)

print(f"\nGenerated: {CASE_ID}")
print(f"Sensor readings: {len(readings)}")
print(f"Events: {len(events)}")
print("Controller: RUNNING throughout")
print(f"Ground truth: {TRUTH}")
