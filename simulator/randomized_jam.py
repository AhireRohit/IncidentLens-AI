
import argparse
import csv
import json
import random
import shutil
from datetime import datetime, timedelta
from pathlib import Path


START = datetime(2026, 1, 15, 14, 0, 0)
DURATION = 1800


def generate(seed):
    rng = random.Random(seed)

    case_id = f"case_{seed:04d}"
    output = Path("data/generated") / case_id
    truth_path = Path("data/ground_truth") / f"{case_id}.json"

    # Protect existing benchmark data.
    if output.exists() or truth_path.exists():
        raise FileExistsError(
            f"{case_id} already exists. Choose another seed."
        )

    # Randomize incident properties.
    fault_second = rng.randint(420, 840)
    trip_second = fault_second + rng.randint(300, 480)

    severity = rng.uniform(0.85, 1.15)
    noise_scale = rng.uniform(0.8, 1.3)

    temperature = 44.0
    ambient = 24.0

    readings = []
    events = []

    current_warning = False
    speed_warning = False

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

        # Progress from healthy operation to severe jam.
        progress = min(
            max(
                (second - fault_second)
                / (trip_second - fault_second),
                0.0
            ),
            1.0
        )

        flow = max(
            0.0,
            rng.gauss(12.0, 0.15 * noise_scale)
        )

        running = second < trip_second

        if running:
            current = max(
                0.0,
                rng.gauss(
                    8.0 + 8.0 * severity * progress,
                    0.15 * noise_scale
                )
            )

            speed = max(
                0.0,
                rng.gauss(
                    1.2 - 1.05 * severity * progress,
                    0.015 * noise_scale
                )
            )

            vibration = max(
                0.0,
                rng.gauss(
                    1.1 + 2.5 * severity * progress,
                    0.05 * noise_scale
                )
            )

            heating = 0.011 * current
            cooling = (
                0.0044
                * (temperature - ambient)
                * (flow / 12.0)
            )

            temperature += (
                heating
                - cooling
                + rng.gauss(0, 0.012 * noise_scale)
            )

        else:
            current = 0.0
            speed = 0.0
            vibration = 0.15

            temperature -= 0.001 * (
                temperature - ambient
            )

        # Round first so event thresholds match saved CSV.
        current = round(current, 2)
        speed = round(speed, 3)
        vibration = round(vibration, 3)

        if running:
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

        elif second == trip_second:
            add_event(
                timestamp,
                "DRIVE_OVERLOAD_TRIP",
                "controller",
                "Controller stopped conveyor after sustained load"
            )

        readings.append({
            "timestamp": timestamp.isoformat(),
            "machine_id": "conveyor_2",
            "motor_temp_c": round(temperature, 2),
            "motor_current_a": current,
            "conveyor_speed_mps": speed,
            "vibration_mm_s": vibration,
            "cooling_flow_lpm": round(flow, 2),
            "controller_state": (
                "RUNNING" if running else "STOPPED"
            )
        })

    # Write the randomized scenario.
    output.mkdir(parents=True, exist_ok=False)
    truth_path.parent.mkdir(parents=True, exist_ok=True)

    with (output / "sensor_readings.csv").open(
        "w", newline="", encoding="utf-8"
    ) as file:
        writer = csv.DictWriter(
            file, fieldnames=readings[0].keys()
        )
        writer.writeheader()
        writer.writerows(readings)

    with (output / "events.jsonl").open(
        "w", encoding="utf-8"
    ) as file:
        for event in events:
            file.write(json.dumps(event) + "\n")

    # Same equipment maintenance history.
    shutil.copyfile(
        "data/generated/mechanical_jam/maintenance.csv",
        output / "maintenance.csv"
    )

    # Evaluation-only ground truth.
    truth = {
        "scenario": case_id,
        "machine_id": "conveyor_2",
        "root_cause": "mechanical_jam",
        "fault_start": (
            START + timedelta(seconds=fault_second)
        ).isoformat(),
        "shutdown_time": (
            START + timedelta(seconds=trip_second)
        ).isoformat(),
        "simulation_parameters": {
            "seed": seed,
            "severity": round(severity, 3),
            "noise_scale": round(noise_scale, 3)
        }
    }

    truth_path.write_text(
        json.dumps(truth, indent=2),
        encoding="utf-8"
    )

    print(f"\nGenerated: {case_id}")
    print(f"Sensor readings: {len(readings)}")
    print(f"Events: {len(events)}")
    print(f"Fault start: {truth['fault_start']}")
    print(f"Shutdown: {truth['shutdown_time']}")
    print(f"Dataset: {output}")
    print(f"Ground truth: {truth_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, required=True)
    args = parser.parse_args()

    if args.seed < 0:
        parser.error("Seed must be nonnegative")

    generate(args.seed)
