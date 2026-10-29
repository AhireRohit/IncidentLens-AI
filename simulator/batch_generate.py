"""Create reproducible synthetic benchmark cases without overwriting existing ones."""
import argparse
import csv
import json
import random
import shutil
from datetime import datetime, timedelta
from pathlib import Path

from simulator.randomized_jam import generate as generate_jam

START = datetime(2026, 1, 15, 14, 0)
SECONDS = 1800
GENERATED = Path('data/generated')
TRUTH = Path('data/ground_truth')
FIELDS = [
    'timestamp', 'machine_id', 'motor_temp_c', 'motor_current_a',
    'conveyor_speed_mps', 'vibration_mm_s', 'cooling_flow_lpm',
    'controller_state',
]
CATEGORIES = (
    'cooling_flow_loss', 'mechanical_jam',
    'temperature_sensor_fault', 'no_fault',
)


def normal_readings(rng):
    rows = []
    for second in range(SECONDS + 1):
        rows.append({
            'timestamp': (START + timedelta(seconds=second)).isoformat(),
            'machine_id': 'conveyor_2',
            'motor_temp_c': round(rng.gauss(44.0, 0.13), 2),
            'motor_current_a': round(rng.gauss(8.0, 0.20), 2),
            'conveyor_speed_mps': round(rng.gauss(1.2, 0.018), 3),
            'vibration_mm_s': round(rng.gauss(1.1, 0.07), 3),
            'cooling_flow_lpm': round(rng.gauss(12.0, 0.18), 2),
            'controller_state': 'RUNNING',
        })
    return rows


def create_case(seed, category):
    case_id = f'case_{seed:04d}'
    directory = GENERATED / case_id
    truth_path = TRUTH / f'{case_id}.json'
    if directory.exists() or truth_path.exists():
        raise FileExistsError(f'{case_id} already exists; no files overwritten')

    if category == 'mechanical_jam':
        # Reuse our already tested randomized mechanical-jam generator.
        generate_jam(seed)
        # Every case shares the same maintenance history: no label leakage.
        shutil.copyfile(
            'data/generated/cooling_failure/maintenance.csv',
            directory / 'maintenance.csv',
        )
        return case_id

    rng = random.Random(seed)
    rows = normal_readings(rng)
    events = []
    fault_second = None
    shutdown_second = None

    def event(second, code, component, message):
        events.append({
            'event_id': f'EVT-{len(events)+1:03d}',
            'timestamp': rows[second]['timestamp'],
            'component': component,
            'event_code': code,
            'message': message,
        })

    if category == 'cooling_flow_loss':
        fault_second = rng.randint(360, 780)
        failed_flow = rng.uniform(0.35, 1.35)
        heating_rate = rng.uniform(0.09, 0.13)
        warned_flow = warned_temp = False
        trip_temp = None

        for second in range(fault_second, SECONDS + 1):
            row = rows[second]
            row['cooling_flow_lpm'] = round(max(0.1, rng.gauss(failed_flow, 0.06)), 2)

            if shutdown_second is None:
                temp = round(
                    44 + heating_rate * (second - fault_second)
                    + rng.gauss(0, 0.10), 2,
                )
                row['motor_temp_c'] = temp
                if row['cooling_flow_lpm'] < 2 and not warned_flow:
                    event(second, 'COOLING_FLOW_LOW', 'cooling_unit',
                          'Cooling flow below 2 L/min')
                    warned_flow = True
                if temp >= 65 and not warned_temp:
                    event(second, 'MOTOR_TEMP_HIGH', 'conveyor_motor',
                          'Motor temperature reached 65 C')
                    warned_temp = True
                if temp >= 75:
                    shutdown_second = second
                    trip_temp = temp
                    event(second, 'THERMAL_SHUTDOWN', 'controller',
                          'Controller stopped conveyor due to overheating')
            else:
                row['motor_temp_c'] = round(
                    max(24.0, trip_temp - 0.015 * (second - shutdown_second)), 2
                )

            if shutdown_second is not None:
                row.update({
                    'motor_current_a': 0.0,
                    'conveyor_speed_mps': 0.0,
                    'vibration_mm_s': 0.15,
                    'controller_state': 'STOPPED',
                })
        if shutdown_second is None or not (warned_flow and warned_temp):
            raise RuntimeError('Cooling case did not produce all three required events')

    elif category == 'temperature_sensor_fault':
        first = rng.randint(420, 740)
        second = rng.randint(1040, 1350)
        fault_second = first
        for start, duration in ((first, rng.randint(8, 14)),
                                (second, rng.randint(8, 14))):
            for index in range(start, start + duration):
                rows[index]['motor_temp_c'] = round(rng.gauss(69.0, 0.4), 2)
        event(first, 'MOTOR_TEMP_HIGH', 'temperature_sensor',
              'Reported motor temperature exceeded 65 C')

    elif category != 'no_fault':
        raise ValueError(f'Unsupported category: {category}')

    directory.mkdir(parents=True)
    TRUTH.mkdir(parents=True, exist_ok=True)
    with (directory / 'sensor_readings.csv').open('w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    with (directory / 'events.jsonl').open('w', encoding='utf-8') as file:
        for item in events:
            file.write(json.dumps(item) + '\n')
    shutil.copyfile('data/generated/cooling_failure/maintenance.csv',
                    directory / 'maintenance.csv')
    truth = {
        'scenario': case_id,
        'machine_id': 'conveyor_2',
        'root_cause': category,
        'fault_start': (START + timedelta(seconds=fault_second)).isoformat()
            if fault_second is not None else None,
        'shutdown_time': (START + timedelta(seconds=shutdown_second)).isoformat()
            if shutdown_second is not None else None,
        'seed': seed,
    }
    truth_path.write_text(json.dumps(truth, indent=2), encoding='utf-8')
    return case_id


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--start-seed', type=int, default=301)
    parser.add_argument('--per-class', type=int, default=2)
    args = parser.parse_args()
    if args.start_seed < 0 or args.per_class < 1:
        parser.error('start-seed must be nonnegative and per-class >= 1')

    categories = list(CATEGORIES) * args.per_class
    random.Random(args.start_seed).shuffle(categories)
    for index, category in enumerate(categories):
        seed = args.start_seed + index
        case_id = f'case_{seed:04d}'
        output = GENERATED / case_id
        truth_path = TRUTH / f'{case_id}.json'
        if output.exists() or truth_path.exists():
            print(f'SKIP {case_id}: existing files (not overwritten)')
            continue
        create_case(seed, category)
        print(f'CREATED {case_id}: {category}')

    print('\nBatch generation finished. AI reports are not generated yet.')


if __name__ == '__main__':
    main()
