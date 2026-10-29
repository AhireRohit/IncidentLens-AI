
import csv
import json
from pathlib import Path


def parse_manual(path):
    """Extract sections from the equipment manual."""
    sections = {}
    current_title = None
    content = []

    for line in Path(path).read_text(
        encoding="utf-8"
    ).splitlines():

        if line.startswith(("## ", "### ")):
            if current_title:
                sections[current_title] = "\n".join(
                    content
                ).strip()

            current_title = line.lstrip("# ").strip()
            content = []

        elif current_title:
            content.append(line)

    if current_title:
        sections[current_title] = "\n".join(
            content
        ).strip()

    return sections


def retrieve_context(
    manual_path,
    maintenance_path,
    events_path,
    machine_id="conveyor_2"
):
    # 1. Load event logs
    with Path(events_path).open(encoding="utf-8") as f:
        events = [
            json.loads(line)
            for line in f
            if line.strip()
        ]

    events.sort(key=lambda e: e["timestamp"])

    # 2. Retrieve manual sections for observed alarms
    manual = parse_manual(manual_path)
    matched_sections = []

    seen_codes = set()

    for event in events:
        code = event["event_code"]

        if code in manual and code not in seen_codes:
            matched_sections.append({
                "source": str(manual_path),
                "section": code,
                "content": manual[code]
            })
            seen_codes.add(code)
            
     
    # 3. Match alarm codes to troubleshooting procedures

    procedure_mapping = {
        "COOLING_FLOW_LOW": ["Procedure A"],
        "MOTOR_TEMP_HIGH": ["Procedure A", "Procedure C"],
        "MOTOR_CURRENT_HIGH": ["Procedure B"],
        "CONVEYOR_SPEED_LOW": ["Procedure B"],
        "DRIVE_OVERLOAD_TRIP": ["Procedure B"]
    }

    event_codes = {
        event["event_code"]
        for event in events
    }

    relevant_procedures = set()

    for code in event_codes:
        relevant_procedures.update(
            procedure_mapping.get(code, [])
        )

    procedures = []

    for title, content in manual.items():
        if any(
            title.startswith(prefix + " ")
            for prefix in relevant_procedures
        ):
            procedures.append({
                "source": str(manual_path),
                "section": title,
                "content": content
            })
       
    # 4. Retrieve relevant maintenance history

    components = {
        event["component"].lower()
        for event in events
    }

    event_codes = {
        event["event_code"]
        for event in events
    }

    # Match alarm types with maintenance-related terminology.
    maintenance_keywords = {
        "COOLING_FLOW_LOW": [
            "cooling", "filter", "pump", "flow"
        ],
        "MOTOR_TEMP_HIGH": [
            "temperature sensor", "sensor calibration",
            "cooling", "thermal"
        ],
        "THERMAL_SHUTDOWN": [
            "cooling", "temperature sensor", "thermal"
        ],
        "MOTOR_CURRENT_HIGH": [
            "motor", "bearing", "belt", "drive"
        ],
        "CONVEYOR_SPEED_LOW": [
            "conveyor", "belt", "bearing", "motor"
        ],
        "DRIVE_OVERLOAD_TRIP": [
            "overload", "drive", "motor", "bearing"
        ]
    }

    search_terms = set()

    for code in event_codes:
        search_terms.update(
            maintenance_keywords.get(code, [])
        )

    with Path(maintenance_path).open(
        newline="", encoding="utf-8-sig"
    ) as f:
        records = list(csv.DictReader(f))

    incident_time = (
        events[0]["timestamp"] if events else None
    )

    relevant_records = []

    for record in records:

        if record["machine_id"] != machine_id:
            continue

        # Exclude maintenance performed after the incident.
        if (
            incident_time is not None
            and record["timestamp"] >= incident_time
        ):
            continue

        component = record["component"].lower()

        searchable_text = " ".join([
            record.get("component", ""),
            record.get("maintenance_type", ""),
            record.get("observation", "")
        ]).lower()

        # Match by component OR relevant maintenance keywords.
        component_match = component in components

        keyword_match = any(
            term in searchable_text
            for term in search_terms
        )

        if component_match or keyword_match:
            relevant_records.append(record)

    # Newest relevant maintenance first.
    relevant_records.sort(
        key=lambda r: r["timestamp"],
        reverse=True
    )


    return {
        "machine_id": machine_id,
        "manual_evidence": matched_sections,
        "troubleshooting_procedures": procedures,
        "maintenance_history": relevant_records
    }


if __name__ == "__main__":
    result = retrieve_context(
        "data/reference/equipment_manual.md",
        "data/generated/cooling_failure/maintenance.csv",
        "data/generated/cooling_failure/events.jsonl"
    )

    print(json.dumps(result, indent=2))
