
# Conveyor 2 — Equipment Manual

Document ID: MAN-FC2-001
Version: 1.0
Equipment: Conveyor Motor, Cooling Unit, Controller

IMPORTANT: This is fictional equipment documentation
created for the AI Incident Investigator simulation.

## 1. Normal Operating Parameters

| Parameter | Normal Range |
|---|---|
| Motor Temperature | 40–55 °C |
| Motor Current | 7–9 A |
| Conveyor Speed | 1.1–1.3 m/s |
| Vibration | 0.8–1.5 mm/s |
| Cooling Flow | 10–14 L/min |

## 2. Alarm Definitions

### COOLING_FLOW_LOW
Triggered when cooling flow falls below 2 L/min.

Possible causes:
- Cooling pump malfunction
- Blocked cooling pipe
- Closed or damaged valve
- Cooling fluid leakage
- Faulty flow sensor

### MOTOR_TEMP_HIGH
Triggered when motor temperature reaches 65 °C.

Possible causes:
- Insufficient cooling
- Excessive mechanical load
- Motor overheating
- Faulty temperature sensor

### THERMAL_SHUTDOWN
Triggered when motor temperature reaches 75 °C.

The controller stops the conveyor to protect
the motor from further overheating.

Expected behavior:
- Conveyor speed becomes zero
- Motor current becomes zero
- Controller state changes to STOPPED


### MOTOR_CURRENT_HIGH

Triggered when motor current reaches or exceeds 12 A.

Possible causes:
- Mechanical obstruction or conveyor jam
- Excessive material load
- Increased belt friction
- Bearing or drive-train resistance

Recommended checks:
- Compare motor current with its normal operating range.
- Check whether conveyor speed decreases.
- Examine vibration readings.
- Inspect the conveyor for mechanical obstructions.

### CONVEYOR_SPEED_LOW

Triggered when conveyor speed falls to 0.6 m/s or below.

Possible causes:
- Mechanical jam
- Excessive belt resistance
- Drive-train malfunction
- Motor or transmission problems

Recommended checks:
- Compare conveyor speed with motor current.
- Check whether vibration increases.
- Review preceding motor-current warnings.

### DRIVE_OVERLOAD_TRIP

The controller stops the conveyor following
a sustained excessive-load condition.

In this simulated scenario, the trip is scheduled
at 14:20:00 after the jam begins at 14:14:00.

This is simplified simulator behavior, not a
physically validated industrial protection algorithm.

Expected behavior:
- Controller state changes to STOPPED.
- Motor current becomes zero.
- Conveyor speed becomes zero.
- Vibration falls to the simulated idle value.

Possible underlying causes:
- Mechanical obstruction
- Excessive conveyor loading
- Bearing or drive-train resistance

Recommended checks:
- Inspect the conveyor for mechanical obstructions.
- Examine motor-current trends.
- Review speed and vibration changes before shutdown.
- Confirm the drive condition before any restart.
```

### 2. Save and verify

Press `Ctrl + S`.

Run:

```powershell
python -c "from investigator.context_retrieval import parse_manual; m=parse_manual('data/reference/equipment_manual.md'); print([k for k in m if k in ['MOTOR_CURRENT_HIGH', 'CONVEYOR_SPEED_LOW', 'DRIVE_OVERLOAD_TRIP']])"
```

Expected output:

```text
['MOTOR_CURRENT_HIGH', 'CONVEYOR_SPEED_LOW', 'DRIVE_OVERLOAD_TRIP']
```

### Why this matters

The AI can now consult the manual to understand that:

- **High motor current + falling speed + increasing vibration** supports a mechanical obstruction.
- **Low cooling flow + rising motor temperature** supports a cooling-related problem.

These patterns help distinguish the two incidents, although neither establishes the exact physical failure by itself.

**That's it for Step 28.** Send me the verification output.

Next we'll adapt our sensor and event analyzers to recognize the mechanical-jam signals instead of assuming every incident is cooling-related. 🚀

## 3. Troubleshooting Procedures

### Procedure A — Cooling Problems

1. Inspect cooling flow readings.
2. Check whether flow decreased before temperature rose.
3. Examine motor temperature trends.
4. Check for cooling-related alarms.
5. Inspect the pump, pipes, valves and flow sensor.
6. Do not confirm a specific component failure
   without supporting evidence.

### Procedure B — Mechanical Jam

1. Check whether motor current increased.
2. Check whether conveyor speed decreased.
3. Examine vibration readings.
4. Review mechanical warnings and maintenance history.

### Procedure C — Temperature Sensor Fault

1. Look for sudden unrealistic temperature jumps.
2. Compare temperature changes with current,
   cooling flow and operating conditions.
3. Check whether other evidence supports overheating.
4. Recommend independent measurement when uncertain.

### Procedure D — Communication Failure

1. Check for missing sensor readings.
2. Examine communication-error events.
3. Inspect controller connection status.
4. Determine whether a timeout caused shutdown.

## 4. Investigation Guidelines

- Distinguish symptoms from root causes.
- Use timestamps to establish event ordering.
- Consider alternative explanations.
- Reference sensor readings and event IDs.
- Identify missing evidence.
- Never claim a component is confirmed faulty
  solely because an alarm was triggered.
