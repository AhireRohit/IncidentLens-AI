
import csv
from pathlib import Path


def predict_baseline(sensor_path):
    """Classify incidents using fixed sensor thresholds."""

    low_cooling = False
    high_current = False
    low_speed = False
    any_anomaly = False
    total_rows = 0

    with Path(sensor_path).open(
        newline="", encoding="utf-8-sig"
    ) as file:
        for row in csv.DictReader(file):
            total_rows += 1

            flow = float(row["cooling_flow_lpm"])
            current = float(row["motor_current_a"])
            speed = float(row["conveyor_speed_mps"])
            temp = float(row["motor_temp_c"])
            vibration = float(row["vibration_mm_s"])
            state = row["controller_state"]

            if state == "RUNNING":
                if flow < 2:
                    low_cooling = True
                if current >= 12:
                    high_current = True
                if speed <= 0.6:
                    low_speed = True

            if (
                flow < 2
                or current < 0
                or current >= 12
                or temp >= 65
                or speed <= 0.6
                or vibration < 0
                or vibration > 1.5
                or state != "RUNNING"
            ):
                any_anomaly = True

    if total_rows == 0:
        return "unknown"

    if low_cooling:
        return "cooling_flow_loss"

    if high_current and low_speed:
        return "mechanical_jam"

    if not any_anomaly:
        return "no_fault"

    return "unknown"


if __name__ == "__main__":
    for scenario in [
        "cooling_failure",
        "mechanical_jam",
        "normal",
        "case_0201"
    ]:
        path = (
            Path("data/generated")
            / scenario
            / "sensor_readings.csv"
        )

        if path.is_file():
            print(
                f"{scenario}: {predict_baseline(path)}"
            )
