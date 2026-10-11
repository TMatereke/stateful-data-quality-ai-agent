import csv
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import first_llm


FIELDS = [
    "ApprovalID",
    "Customer",
    "ReplacementRevenue",
    "ApprovalStatus",
    "ApprovedBy",
    "ApprovedAt",
    "ConsumedAt",
]


class TestApprovalLifecycle(unittest.TestCase):

    def setUp(self):
        # Use an isolated temporary directory.
        self.original_cwd = os.getcwd()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)

        os.chdir(self.temp_dir.name)
        self.addCleanup(os.chdir, self.original_cwd)

        Path("day01").mkdir()

        self.registry = Path("day01") / "approval_registry.csv"

        self.write_registry([
            {
                "ApprovalID": "TEST-001",
                "Customer": "Globex",
                "ReplacementRevenue": "62000",
                "ApprovalStatus": "PENDING",
                "ApprovedBy": "",
                "ApprovedAt": "",
                "ConsumedAt": "",
            }
        ])

        # Prevent tests from writing to the real audit log.
        audit_patch = patch("first_llm.log_agent_action")
        self.mock_audit = audit_patch.start()
        self.addCleanup(audit_patch.stop)

    def write_registry(self, rows):
        with open(
            self.registry,
            "w",
            newline="",
            encoding="utf-8",
        ) as file:
            writer = csv.DictWriter(
                file,
                fieldnames=FIELDS,
            )
            writer.writeheader()
            writer.writerows(rows)

    def read_registry(self):
        with open(
            self.registry,
            "r",
            newline="",
            encoding="utf-8",
        ) as file:
            return list(csv.DictReader(file))

    def test_pending_approval_cannot_be_consumed(self):
        """A pending request must not authorize remediation."""

        result = first_llm.consume_remediation_approval(
            "TEST-001"
        )

        self.assertEqual(result["status"], "NOT_CONSUMED")

        row = self.read_registry()[0]
        self.assertEqual(row["ApprovalStatus"], "PENDING")
        self.assertEqual(row["ConsumedAt"], "")

    def test_approved_request_can_be_consumed_once(self):
        """A valid human approval can be consumed only once."""

        approval = first_llm.approve_remediation_request(
            approval_id="TEST-001",
            approved_by="TestReviewer",
        )

        self.assertEqual(approval["status"], "APPROVED")
        self.assertEqual(
            approval["approved_by"],
            "TestReviewer",
        )

        row = self.read_registry()[0]
        self.assertEqual(row["ApprovalStatus"], "APPROVED")

        consumption = first_llm.consume_remediation_approval(
            "TEST-001"
        )

        self.assertEqual(consumption["status"], "CONSUMED")

        row = self.read_registry()[0]
        self.assertEqual(row["ApprovalStatus"], "CONSUMED")
        self.assertNotEqual(row["ConsumedAt"], "")

        # Replay must fail.
        replay = first_llm.consume_remediation_approval(
            "TEST-001"
        )

        self.assertEqual(replay["status"], "NOT_CONSUMED")

        row = self.read_registry()[0]
        self.assertEqual(row["ApprovalStatus"], "CONSUMED")

    def test_missing_approver_is_rejected(self):
        """An approval without an approver identity must fail."""

        result = first_llm.approve_remediation_request(
            approval_id="TEST-001",
            approved_by="   ",
        )

        self.assertEqual(result["status"], "REJECTED")

        row = self.read_registry()[0]
        self.assertEqual(row["ApprovalStatus"], "PENDING")
        self.assertEqual(row["ApprovedBy"], "")


if __name__ == "__main__":
    unittest.main(verbosity=2)