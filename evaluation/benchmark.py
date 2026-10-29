
import json
from pathlib import Path

from evaluation.evaluate import evaluate_scenario
from evaluation.baseline import predict_baseline


GENERATED = Path("data/generated")
GROUND_TRUTH = Path("data/ground_truth")


def discover_scenarios():
    """Find all generated cases with ground truth and sensors."""

    return sorted(
        folder.name
        for folder in GENERATED.iterdir()
        if folder.is_dir()
        and (folder / "sensor_readings.csv").is_file()
        and (
            GROUND_TRUTH / f"{folder.name}.json"
        ).is_file()
    )


def run_benchmark():
    scenarios = discover_scenarios()

    if not scenarios:
        print("No benchmark scenarios found.")
        return

    results = []

    print("\n=== AI INCIDENT BENCHMARK ===\n")

    for scenario in scenarios:
        folder = GENERATED / scenario

        truth = json.loads(
            (
                GROUND_TRUTH / f"{scenario}.json"
            ).read_text(encoding="utf-8")
        )

        actual = truth["root_cause"]

        baseline_prediction = predict_baseline(
            folder / "sensor_readings.csv"
        )

        baseline_correct = (
            baseline_prediction == actual
        )

        ai_prediction = None
        ai_correct = False
        evidence_passed = False
        report_error = None

        report_path = (
            folder / "checked_investigation.json"
        )

        if report_path.is_file():
            try:
                evaluation = evaluate_scenario(scenario)

                ai_prediction = evaluation[
                    "predicted_root_cause"
                ]
                ai_correct = evaluation["correct"]
                evidence_passed = evaluation[
                    "evidence_checks_passed"
                ]

            except (
                OSError,
                ValueError,
                KeyError,
                TypeError,
            ) as exc:
                report_error = str(exc)

        else:
            report_error = "No checked investigation"

        # A correct label alone is insufficient.
        # The investigation must also pass evidence checks.
        ai_success = ai_correct and evidence_passed

        result = {
            "scenario": scenario,
            "actual_root_cause": actual,
            "ai_prediction": ai_prediction,
            "ai_correct": ai_correct,
            "evidence_passed": evidence_passed,
            "ai_end_to_end_success": ai_success,
            "baseline_prediction": baseline_prediction,
            "baseline_correct": baseline_correct,
            "report_error": report_error,
        }

        results.append(result)

        ai_status = (
            "PASS" if ai_success
            else "FAIL" if ai_prediction is not None
            else "NO VALID REPORT"
        )

        baseline_status = (
            "PASS" if baseline_correct else "FAIL"
        )

        print(f"Scenario: {scenario}")
        print(f"  AI:       {ai_status}")
        print(
            f"  Baseline: {baseline_prediction} "
            f"({baseline_status})"
        )

    total = len(results)

    validated = sum(
        r["evidence_passed"] for r in results
    )

    ai_successes = sum(
        r["ai_end_to_end_success"] for r in results
    )

    baseline_correct = sum(
        r["baseline_correct"] for r in results
    )

    summary = {
        "total_incidents": total,
        "validated_reports": validated,
        "missing_or_invalid_reports": total - validated,
        "ai_accuracy_on_validated_reports": (
            round(ai_successes / validated, 4)
            if validated else None
        ),
        "ai_end_to_end_success_rate": round(
            ai_successes / total, 4
        ),
        "baseline_accuracy": round(
            baseline_correct / total, 4
        ),
        "evidence_validation_pass_rate": round(
            validated / total, 4
        ),
        "scenario_results": results,
        "evaluation_type": "synthetic_development_benchmark",
    }

    output = Path(
        "data/evaluation/benchmark_summary.json"
    )
    output.parent.mkdir(parents=True, exist_ok=True)

    output.write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8"
    )

    print("\n=== BENCHMARK SUMMARY ===")
    print(json.dumps({
        key: value
        for key, value in summary.items()
        if key not in (
            "scenario_results",
            "evaluation_type"
        )
    }, indent=2))

    print(f"\nSaved to: {output}")


if __name__ == "__main__":
    run_benchmark()
