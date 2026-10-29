import csv
import re
from datetime import datetime
from pathlib import Path


DATE_PATTERN = re.compile(
    r"\b(?:\d{1,2}\s+[A-Za-z]+\s+\d{4}"
    r"|\d{4}-\d{2}-\d{2})\b"
)


def normalize_text(text):
    for character in "-‐‑‒–—―−":
        text = text.replace(character, "-")
    return " ".join(text.split())


def parse_date(value):
    for fmt in ("%d %b %Y", "%d %B %Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def validate_maintenance_dates(report_text, csv_path):
    with Path(csv_path).open(
        newline="", encoding="utf-8-sig"
    ) as file:
        records = {
            row["record_id"]: row
            for row in csv.DictReader(file)
        }

    errors = []
    checked = 0

    for line_number, raw_line in enumerate(
        report_text.splitlines(), start=1
    ):
        line = normalize_text(raw_line)

        ids = set(re.findall(r"\bMNT-\d+\b", line))
        dates = DATE_PATTERN.findall(line)

        # Only check unambiguous ID/date pairs
        if len(ids) != 1 or len(dates) != 1:
            continue

        record_id = next(iter(ids))
        reported_date = parse_date(dates[0])

        if reported_date is None:
            continue

        if record_id not in records:
            errors.append(
                f"Line {line_number}: Unknown record {record_id}"
            )
            continue

        actual_date = datetime.fromisoformat(
            records[record_id]["timestamp"]
        ).date()

        checked += 1

        if reported_date != actual_date:
            errors.append(
                f"Line {line_number}: {record_id} "
                f"reported as {reported_date}, "
                f"but actual date is {actual_date}"
            )

    return {
        "checked_date_references": checked,
        "errors": errors,
        "passed": checked > 0 and len(errors) == 0,
        "validation_scope" : (
            "Only unambiguous maintenance ID/date pairs"
            "on the same line are checked. "
        )
    }
    

def validate_structured_maintenance_dates(report, csv_path):

    with Path(csv_path).open(
        newline="", encoding="utf-8-sig"
    ) as file:
        records = {
            row["record_id"]: row
            for row in csv.DictReader(file)
        }

    errors = []
    checked = 0
    maintenance_count = 0

    evidence = report.get("supporting_evidence", [])

    if not isinstance(evidence, list):
        return {
            "checked_date_references": 0,
            "errors": ["supporting_evidence must be a list"],
            "passed": False
        }

    for item in evidence:
        if not isinstance(item, dict):
            continue

        if item.get("source_type") != "maintenance":
            continue

        maintenance_count += 1

        record_id = item.get("reference")
        finding = item.get("finding", "")

        if record_id not in records:
            errors.append(f"Unknown maintenance ID: {record_id}")
            continue

        if not isinstance(finding, str):
            errors.append(f"{record_id}: finding must be text")
            continue

        dates = DATE_PATTERN.findall(normalize_text(finding))

        if len(dates) != 1:
            errors.append(
                f"{record_id}: expected exactly one date, "
                f"found {len(dates)}"
            )
            continue

        reported_date = parse_date(dates[0])

        actual_date = datetime.fromisoformat(
            records[record_id]["timestamp"]
        ).date()

        checked += 1

        if reported_date != actual_date:
            errors.append(
                f"{record_id}: AI reported {reported_date}, "
                f"actual date is {actual_date}"
            )

    
    return {
        "maintenance_references": maintenance_count,
        "checked_date_references": checked,
        "errors": errors,
        "citation_coverage": (
            "citations_checked"
            if maintenance_count > 0
            else "no_maintenance_citations"
        ),
        "passed": (
            checked == maintenance_count
            and not errors
        )
    }


