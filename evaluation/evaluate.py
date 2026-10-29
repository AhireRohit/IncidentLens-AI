
import argparse
import json
from pathlib import Path


ROOT = Path("data")

VALID_CATEGORIES = {
    "cooling_flow_loss",
    "mechanical_jam",
    "temperature_sensor_fault",
    "communication_outage",
    "no_fault",
    "unknown"
}


def evaluate_scenario(scenario):

    # AI-generated report
    report_path = (
        ROOT / "generated" / scenario
        / "checked_investigation.json"
    )

    # Hidden ground truth (evaluation ONLY)
    truth_path = (
        ROOT / "ground_truth" / f"{scenario}.json"
    )

    if not report_path.is_file():
        raise FileNotFoundError(report_path)

    if not truth_path.is_file():
        raise FileNotFoundError(truth_path)

    # Load AI report
    saved = json.loads(
        report_path.read_text(encoding="utf-8")
    )

    report = saved["report"]

    # Load actual injected cause
    truth = json.loads(
        truth_path.read_text(encoding="utf-8")
    )

    if truth["scenario"] != scenario:
        raise ValueError("Ground-truth scenario mismatch")

    predicted = report.get("root_cause_category")
    actual = truth["root_cause"]

    if predicted not in VALID_CATEGORIES:
        raise ValueError(
            f"Invalid predicted category: {predicted}"
        )

    if actual not in VALID_CATEGORIES:
        raise ValueError(
            f"Invalid ground-truth category: {actual}"
        )

    # Verify the saved evidence checks
    validation = saved.get("validation", {})

    required_checks = [
        "sensor_validation",
        "reference_validation",
        "maintenance_validation"
    ]

    checks_passed = (
        saved.get("status") == "AUTOMATED_CHECKS_PASSED"
        and all(
            validation.get(name, {}).get("passed") is True
            for name in required_checks
        )
    )

    # Root-cause evaluation
    correct = predicted == actual

    result = {
        "scenario": scenario,
        "actual_root_cause": actual,
        "predicted_root_cause": predicted,
        "correct": correct,
        "classification_score": int(correct),
        "confidence": report.get("confidence"),
        "evidence_checks_passed": checks_passed
    }

    # Save evaluation separately
    output_dir = ROOT / "evaluation"
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / f"{scenario}_evaluation.json"

    output_path.write_text(
        json.dumps(result, indent=2),
        encoding="utf-8"
    )

    return result


if __name__ == "__main__":

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--scenario",
        required=True
    )

    args = parser.parse_args()

    if (
        not args.scenario.isidentifier()
        or args.scenario.startswith("_")
    ):
        parser.error("Invalid scenario name")

    result = evaluate_scenario(args.scenario)

    print("\n=== ROOT CAUSE EVALUATION ===")
    print(json.dumps(result, indent=2))
