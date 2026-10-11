
import csv
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import first_llm


CUSTOMER_FIELDS = ["RecordID", "Customer", "Revenue"]

APPROVAL_FIELDS = [
    "ApprovalID",
    "Customer",
    "ReplacementRevenue",
    "ApprovalStatus",
    "ApprovedBy",
    "ApprovedAt",
    "ConsumedAt",
]


class TestEndToEndWorkflow(unittest.TestCase):

    def setUp(self):
        self.original_cwd = os.getcwd()
        self.temp_dir = tempfile.TemporaryDirectory()

        # Register cleanup so the working directory is restored
        # before Windows attempts to delete the temporary folder.
        self.addCleanup(self.temp_dir.cleanup)
        os.chdir(self.temp_dir.name)
        self.addCleanup(os.chdir, self.original_cwd)

        Path("day01").mkdir()

        self.customer_file = Path("day01") / "customers.csv"
        self.approval_file = (
            Path("day01") / "approval_registry.csv"
        )

        self.write_customer(-62000)
        self.write_approval("PENDING")

        # Keep durable memory isolated in this test.
        self.memory = {
            "version": 2,
            "messages": [],
            "summary": "",
            "conversation_id": None,
            "session_updated_at": None,
            "memory_context": {
                "active_customer": None,
                "last_topic": None,
                "last_tool": None,
                "last_approval_id": None,
                "last_workflow_status": None,
                "last_business_snapshot": None,
                "customers": {},
            },
        }

        # Prevent tests from writing to real audit/state/memory files.
        self.patchers = [
            patch(
                "first_llm.load_conversation_memory",
                side_effect=lambda: self.memory,
            ),
            patch("first_llm.save_conversation_memory"),
            patch("first_llm.log_agent_action"),
            patch("first_llm.update_audit_verification"),
            patch("first_llm.update_last_run_state"),
        ]

        for patcher in self.patchers:
            patcher.start()
            self.addCleanup(patcher.stop)

    def write_customer(self, revenue):
        with open(
            self.customer_file,
            "w",
            newline="",
            encoding="utf-8",
        ) as file:
            writer = csv.DictWriter(
                file,
                fieldnames=CUSTOMER_FIELDS,
            )
            writer.writeheader()
            writer.writerow({
                "RecordID": "1",
                "Customer": "Globex",
                "Revenue": str(revenue),
            })

    def write_approval(self, status):
        with open(
            self.approval_file,
            "w",
            newline="",
            encoding="utf-8",
        ) as file:
            writer = csv.DictWriter(
                file,
                fieldnames=APPROVAL_FIELDS,
            )
            writer.writeheader()
            writer.writerow({
                "ApprovalID": "TEST-E2E-001",
                "Customer": "Globex",
                "ReplacementRevenue": "62000",
                "ApprovalStatus": status,
                "ApprovedBy": "",
                "ApprovedAt": "",
                "ConsumedAt": "",
            })

    def read_customer_revenue(self):
        with open(
            self.customer_file,
            "r",
            newline="",
            encoding="utf-8",
        ) as file:
            rows = list(csv.DictReader(file))

        return int(rows[0]["Revenue"])

    def read_approval(self):
        with open(
            self.approval_file,
            "r",
            newline="",
            encoding="utf-8",
        ) as file:
            return next(csv.DictReader(file))

    def test_approved_remediation_completes_workflow(self):
        """Approval, remediation, consumption and verification pass."""

        approval = first_llm.approve_remediation_request(
            approval_id="TEST-E2E-001",
            approved_by="TestReviewer",
        )

        self.assertEqual(approval["status"], "APPROVED")

        result = first_llm.run_quality_workflow()

        self.assertEqual(result["final_status"]["status"], "PASS")
        self.assertEqual(
            result["verification"]["verification_status"],
            "PASS",
        )

        item = result["remediation_summary"][0]

        self.assertEqual(
            item["remediation_result"]["status"],
            "FIXED",
        )
        self.assertEqual(
            item["consumption_result"]["status"],
            "CONSUMED",
        )

        self.assertEqual(self.read_customer_revenue(), 62000)
        self.assertEqual(
            self.read_approval()["ApprovalStatus"],
            "CONSUMED",
        )

    def test_pending_approval_does_not_change_revenue(self):
        """Without approval, the workflow must not repair revenue."""

        result = first_llm.run_quality_workflow()

        self.assertEqual(result["final_status"]["status"], "FAIL")
        self.assertEqual(
            result["verification"]["verification_status"],
            "FAIL",
        )

        item = result["remediation_summary"][0]

        self.assertIsNone(item["remediation_result"])
        self.assertIsNone(item["consumption_result"])

        self.assertEqual(self.read_customer_revenue(), -62000)
        self.assertEqual(
            self.read_approval()["ApprovalStatus"],
            "PENDING",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)