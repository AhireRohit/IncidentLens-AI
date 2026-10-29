
import csv
import tempfile
import unittest
from pathlib import Path

from investigator.report_validation import (
    validate_maintenance_dates
)


class TestReportValidation(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.csv_path = (
            Path(self.temp_dir.name) / "maintenance.csv"
        )

        with self.csv_path.open(
            "w", newline="", encoding="utf-8"
        ) as file:
            writer = csv.writer(file)
            writer.writerow([
                "record_id", "timestamp"
            ])
            writer.writerow([
                "MNT-002", "2026-01-06T09:30:00"
            ])

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_correct_date(self):
        report = "MNT-002 was performed on 6 Jan 2026."

        result = validate_maintenance_dates(
            report, self.csv_path
        )

        self.assertTrue(result["passed"])
        self.assertEqual(result["checked_date_references"], 1)

    def test_incorrect_date(self):
        report = "MNT-002 was performed on 13 Jan 2026."

        result = validate_maintenance_dates(
            report, self.csv_path
        )

        self.assertFalse(result["passed"])
        self.assertEqual(len(result["errors"]), 1)

    def test_unicode_hyphen(self):
        report = "MNT‑002 was performed on 6 Jan 2026."

        result = validate_maintenance_dates(
            report, self.csv_path
        )

        self.assertTrue(result["passed"])

    def test_no_date_checked(self):
        report = "The cooling filter was cleaned."

        result = validate_maintenance_dates(
            report, self.csv_path
        )

        self.assertFalse(result["passed"])
        self.assertEqual(result["checked_date_references"], 0)


if __name__ == "__main__":
    unittest.main()
