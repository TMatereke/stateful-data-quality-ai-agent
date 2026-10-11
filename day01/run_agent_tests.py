
import json
import unittest
from datetime import datetime
from pathlib import Path

import test_memory_routing
import test_write_guardrails
import test_approval_lifecycle
import test_end_to_end_workflow
import test_fix_authorization


TEST_GROUPS = [
    ("Memory routing", test_memory_routing),
    ("Write guardrails", test_write_guardrails),
    ("Approval lifecycle", test_approval_lifecycle),
    ("End-to-end workflow", test_end_to_end_workflow),
    ("Remediation authorization", test_fix_authorization),
]

REPORT_FILE = Path(__file__).with_name("agent_test_report.json")


def main():
    group_results = []
    total_run = 0
    total_passed = 0
    total_failed = 0
    total_skipped = 0

    for group_name, module in TEST_GROUPS:
        suite = unittest.defaultTestLoader.loadTestsFromModule(module)

        # Run each test group independently to provide a clear summary.
        runner = unittest.TextTestRunner(verbosity=1)
        result = runner.run(suite)

        failed = len(result.failures) + len(result.errors)
        skipped = len(result.skipped)
        passed = result.testsRun - failed - skipped

        group_results.append({
            "group": group_name,
            "status": "PASS" if result.wasSuccessful() else "FAIL",
            "tests_run": result.testsRun,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
        })

        total_run += result.testsRun
        total_passed += passed
        total_failed += failed
        total_skipped += skipped

    overall_status = (
        "PASS"
        if all(group["status"] == "PASS" for group in group_results)
        else "FAIL"
    )

    report = {
        "generated_at": datetime.now().astimezone().isoformat(),
        "overall_status": overall_status,
        "total_tests": total_run,
        "passed": total_passed,
        "failed": total_failed,
        "skipped": total_skipped,
        "groups": group_results,
    }

    # Write to a temporary file before replacing the report.
    temporary_file = REPORT_FILE.with_suffix(".tmp")
    temporary_file.write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    temporary_file.replace(REPORT_FILE)

    print("\n===== AGENT REGRESSION REPORT =====")

    for group in group_results:
        print(
            f"{group['group']}: {group['status']} — "
            f"{group['passed']} passed, "
            f"{group['failed']} failed, "
            f"{group['skipped']} skipped"
        )

    print("-----------------------------------")
    print(
        f"TOTAL: {total_run} tests | "
        f"{total_passed} passed | "
        f"{total_failed} failed | "
        f"{total_skipped} skipped"
    )
    print(f"OVERALL STATUS: {overall_status}")
    print(f"Report saved to: {REPORT_FILE}")

    if overall_status != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()