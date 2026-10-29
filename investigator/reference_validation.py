import csv
import json
from pathlib import Path

from investigator.context_retrieval import parse_manual


def validate_references(
    report,
    events_path,
    maintenance_path,
    manual_path
):
    # Load real event identifiers
    with Path(events_path).open(encoding="utf-8") as f:
        event_ids = {
            json.loads(line)["event_id"]
            for line in f
            if line.strip()
        }

    # Load real maintenance identifiers
    with Path(maintenance_path).open(
        newline="", encoding="utf-8-sig"
    ) as f:
        maintenance_ids = {
            row["record_id"]
            for row in csv.DictReader(f)
        }

    # Load exact manual section headings
    manual_ids = set(parse_manual(manual_path))

    known = {
        "event": event_ids,
        "manual": manual_ids,
        "maintenance": maintenance_ids
    }

    errors = []
    checked = 0
    
    
    # Empty event timelines and citations are allowed only
    # when the report says no fault AND the actual event log is empty.
    allow_empty = (
        report.get("root_cause_category") == "no_fault"
        and len(event_ids) == 0
    )


    # Validate supporting evidence references
    entries = report.get("supporting_evidence")

    if not isinstance(entries, list):
        errors.append(
            "supporting_evidence must be a nonempty "
            "list of structured references"
        )
    elif not entries and not allow_empty:
        errors.append(
            "supporting_evidence cannot be empty for this incident"
        )    
    
    else:
        for index, item in enumerate(entries, 1):
            if not isinstance(item, dict):
                errors.append(
                    f"Citation {index}: expected an object, not text"
                )
                continue

            kind = item.get("source_type")
            ref = item.get("reference")

            if kind not in known:
                errors.append(
                    f"Citation {index}: invalid source_type {kind!r}"
                )
                continue

            if not isinstance(ref, str) or not ref:
                errors.append(
                    f"Citation {index}: missing reference"
                )
                continue

            checked += 1

            if ref not in known[kind]:
                errors.append(
                    f"Citation {index}: unknown "
                    f"{kind} reference {ref!r}"
                )

    # Validate timeline event references
    timeline = report.get("timeline")

    if not isinstance(timeline, list):
        errors.append("timeline must be a nonempty list")
        
    elif not timeline and not allow_empty:
        errors.append(
            "timeline cannot be empty for this incident"
        )
    else:
        for index, item in enumerate(timeline, 1):
            if not isinstance(item, dict):
                errors.append(
                    f"Timeline {index}: expected an object"
                )
                continue

            ref = item.get("evidence_reference")

            if not isinstance(ref, str) or not ref:
                errors.append(
                    f"Timeline {index}: missing evidence_reference"
                )
                continue

            checked += 1

            if ref not in event_ids:
                errors.append(
                    f"Timeline {index}: unknown "
                    f"event reference {ref!r}"
                )
                
    
    # Validate the structure of narrative fields.
    # These fields must contain text, not citation objects.
    narrative_fields = (
        "alternative_explanations",
        "missing_evidence",
        "recommended_checks",
    )

    for field in narrative_fields:
        items = report.get(field)

        if not isinstance(items, list):
            errors.append(
                f"{field} must be a list of strings"
            )
            continue

        for index, item in enumerate(items, 1):
            if not isinstance(item, str):
                errors.append(
                    f"{field}[{index}] must be text, "
                    "not a structured object"
                )


    return {
        "checked_references": checked,
        "errors": errors,
        "passed": (checked > 0 or allow_empty) and not errors
    }
