
import argparse
import json
from pathlib import Path

import pandas as pd


def analyze_sensors(csv_path):
    df = pd.read_csv(csv_path, parse_dates=["timestamp"])
    df = df.sort_values("timestamp").reset_index(drop=True)

    # Find the first occurrence of a condition
    def first_occurrence(condition):
        matches = df.loc[condition, "timestamp"]
        if matches.empty:
            return None
        return matches.iloc[0].isoformat()

    # Thresholds from our fictional equipment manual
    
    # Cooling-related anomalies
    cooling_low = df["cooling_flow_lpm"] < 2
    temperature_high = df["motor_temp_c"] >= 65

    # Mechanical-related anomalies
    current_high = df["motor_current_a"] >= 12
    
    # Detect abnormal low speed only while the conveyor
    # is still operating, not after a controller shutdown.
    speed_low = (
        (df["conveyor_speed_mps"] <= 0.6)
        & (df["controller_state"] == "RUNNING")
    )

    vibration_high = df["vibration_mm_s"] > 1.5

    # Equipment shutdown
    stopped = df["controller_state"] == "STOPPED"


    shutdown_time = first_occurrence(stopped)

    # Reference: first five minutes of operation
    baseline_end = df["timestamp"].iloc[0] + pd.Timedelta(minutes=5)
    baseline = df[df["timestamp"] < baseline_end]

    # Inspect two minutes immediately before shutdown
    if shutdown_time:
        stop_ts = pd.Timestamp(shutdown_time)
        recent = df[
            (df["timestamp"] >= stop_ts - pd.Timedelta(minutes=2))
            & (df["timestamp"] < stop_ts)
        ]
    else:
        recent = df.tail(120)

    def averages(frame):
        columns = [
            "cooling_flow_lpm",
            "motor_temp_c",
            "motor_current_a",
            "conveyor_speed_mps",
            "vibration_mm_s",
        ]
        return {
            col: round(float(frame[col].mean()), 2)
            for col in columns
        }

    report = {
        "machine_id": df["machine_id"].iloc[0],
        "total_readings": len(df),
        "first_low_cooling_flow": first_occurrence(cooling_low),
        "first_high_temperature": first_occurrence(temperature_high),
        "first_high_motor_current": first_occurrence(current_high),
        "first_low_conveyor_speed": first_occurrence(speed_low),
        "first_high_vibration": first_occurrence(vibration_high),
        "first_shutdown": shutdown_time,
        "maximum_temperature_c": float(df["motor_temp_c"].max()),
        "baseline_averages": averages(baseline),
        "pre_shutdown_averages": averages(recent),
    }

    
    # Detect abrupt temperature changes between
    # consecutive one-second sensor readings.
    temperature_steps = (
        df["motor_temp_c"].diff().abs().fillna(0)
    )

    report["largest_temp_step_c"] = round(
        float(temperature_steps.max()), 2
    )

    
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--csv",
        type=Path,
        default=Path(
            "data/generated/cooling_failure/sensor_readings.csv"
        ),
    )
    args = parser.parse_args()

    result = analyze_sensors(args.csv)
    print(json.dumps(result, indent=2))
