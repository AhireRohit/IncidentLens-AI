
import csv
import random
from pathlib import Path
from datetime import datetime, timedelta

# Reproducible simulation
random_generator = random.Random(42)

START_TIME = datetime(2026, 1, 15, 14, 0, 0)
DURATION_SECONDS = 30 * 60

OUTPUT_FILE = Path("data/generated/normal/sensor_readings.csv")
OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

motor_temperature = 44.0
ambient_temperature = 24.0

with OUTPUT_FILE.open("w", newline="", encoding="utf-8") as file:
    writer = csv.writer(file)

    writer.writerow([
        "timestamp",
        "machine_id",
        "motor_temp_c",
        "motor_current_a",
        "conveyor_speed_mps",
        "vibration_mm_s",
        "cooling_flow_lpm",
        "controller_state"
    ])

    for second in range(DURATION_SECONDS + 1):

        timestamp = START_TIME + timedelta(seconds=second)

        motor_current = random_generator.gauss(8.0, 0.25)
        conveyor_speed = random_generator.gauss(1.2, 0.02)
        vibration = random_generator.gauss(1.1, 0.09)
        cooling_flow = random_generator.gauss(12.0, 0.2)

        # Simplified heat generation and cooling model
        heating = 0.011 * motor_current
        cooling = (
            0.0044
            * (motor_temperature - ambient_temperature)
            * (cooling_flow / 12.0)
        )

        motor_temperature += (
            heating
            - cooling
            + random_generator.gauss(0, 0.012)
        )

        writer.writerow([
            timestamp.isoformat(),
            "conveyor_2",
            round(motor_temperature, 2),
            round(motor_current, 2),
            round(conveyor_speed, 3),
            round(vibration, 3),
            round(cooling_flow, 2),
            "RUNNING"
        ])

print(f"Simulation complete: {DURATION_SECONDS + 1} readings generated")
print(f"Saved to: {OUTPUT_FILE}")
