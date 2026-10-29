
import json
from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

DATA_DIR = Path("data/generated/cooling_failure")

# Load sensor readings
df = pd.read_csv(
    DATA_DIR / "sensor_readings.csv",
    parse_dates=["timestamp"]
)

# Load events
with (DATA_DIR / "events.jsonl").open(encoding="utf-8") as f:
    events = [json.loads(line) for line in f if line.strip()]

# Create three synchronized graphs
fig, axes = plt.subplots(
    3, 1, figsize=(13, 9), sharex=True
)

signals = [
    ("cooling_flow_lpm", "Cooling Flow (L/min)"),
    ("motor_temp_c", "Motor Temperature (°C)"),
    ("conveyor_speed_mps", "Conveyor Speed (m/s)")
]

for ax, (column, label) in zip(axes, signals):
    ax.plot(df["timestamp"], df[column], linewidth=1.5, color="blue", label=label)
    ax.set_ylabel(label)
    ax.grid(True, alpha=0.3)
    ax.legend(loc="upper left")

    # Add vertical markers at event timestamps
    for event in events:
        event_time = pd.to_datetime(event["timestamp"])
        ax.axvline(
            event_time,
            color="red",
            linestyle="--",
            alpha=0.6
        )

# Show temperature thresholds
axes[1].axhline(
    65, color="orange", linestyle=":",
    label="Warning threshold (65°C)"
)
axes[1].axhline(
    75, color="red", linestyle=":",
    label="Shutdown threshold (75°C)"
)
axes[1].legend()

# Label events on first graph
for event in events:
    event_time = pd.to_datetime(event["timestamp"])
    axes[0].text(
        event_time,
        0.97,
        event["event_code"],
        rotation=90,
        fontsize=8,
        ha="right",
        va="top",
        transform=axes[0].get_xaxis_transform()
    )

axes[-1].xaxis.set_major_formatter(
    mdates.DateFormatter("%H:%M")
)
axes[-1].set_xlabel("Time")

fig.suptitle(
    "AI Incident Investigator — Cooling Failure",
    fontsize=15,
    fontweight="bold"
)

plt.tight_layout()

output_file = DATA_DIR / "incident_chart.png"
plt.savefig(output_file, dpi=160)

print(f"Chart saved to: {output_file}")

plt.show()
