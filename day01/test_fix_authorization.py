
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

APPROVED_AT = "2026-10-11T12:00:00"


class TestFixAuthorization(unittest.TestCase):

    def setUp(self):
        self.original_cwd = os.getcwd()
        self.temp_dir = tempfile.TemporaryDirectory()

            # Register directory cleanup first.
        self.addCleanup(self.temp_dir.cleanup)

            # Change into the temporary directory.
        os.chdir(self.temp_dir.name)

            # Register restoration second.
            # unittest runs cleanups in reverse order, so we leave
            # the temporary directory before deleting it.
        self.addCleanup(os.chdir, self.original_cwd)

        Path("day01").mkdir()

        self.customer_file = Path("day01") / "customers.csv"
        self.approval_file = (
            Path("day01") / "approval_registry.csv"
        )

        with open(
            self.customer_file,
            "w",
            newline="",
            encoding="utf-8",
        ) as file:
            writer = csv.DictWriter(
                file,
                fieldnames=["RecordID", "Customer", "Revenue"],
            )
            writer.writeheader()
            writer.writerow({
                "RecordID": "1",
                "Customer": "Globex",
                "Revenue": "-62000",
            })

        self.write_approval("PENDING")

        # Mock customer lookup and audit logging.
        data_patch = patch(
            "first_llm.get_customer_data_from_csv",
            return_value={"Globex": -62000},
        )
        data_patch.start()
        self.addCleanup(data_patch.stop)

        audit_patch = patch("first_llm.log_agent_action")
        audit_patch.start()
        self.addCleanup(audit_patch.stop)

    def write_approval(
        self,
        status,
        approval_id="TEST-001",
        replacement="62000",
        approved_by="TestReviewer",
        approved_at=APPROVED_AT,
    ):
        row = {
            "ApprovalID": approval_id,
            "Customer": "Globex",
            "ReplacementRevenue": str(replacement),
            "ApprovalStatus": status,
            "ApprovedBy": approved_by,
            "ApprovedAt": approved_at,
            "ConsumedAt": "",
        }

        with open(
            self.approval_file,
            "w",
            newline="",
            encoding="utf-8",
        ) as file:
            writer = csv.DictWriter(
                file,
                fieldnames=FIELDS,
            )
            writer.writeheader()
            writer.writerow(row)

    def run_fix(
        self,
        approval_id="TEST-001",
        replacement=62000,
        approved_by="TestReviewer",
        approved_at=APPROVED_AT,
    ):
        return first_llm.fix_negative_revenue(
            customer="Globex",
            replacement_revenue=replacement,
            approval_id=approval_id,
            approved_by=approved_by,
            approved_at=approved_at,
        )

    def read_revenue(self):
        with open(
            self.customer_file,
            "r",
            newline="",
            encoding="utf-8",
        ) as file:
            rows = list(csv.DictReader(file))

        return rows[0]["Revenue"]

    def test_missing_approval_id_is_rejected(self):
        result = self.run_fix(approval_id=None)

        self.assertEqual(result["status"], "REJECTED")
        self.assertEqual(self.read_revenue(), "-62000")

    def test_pending_approval_is_rejected(self):
        result = self.run_fix()

        self.assertEqual(result["status"], "REJECTED")
        self.assertEqual(self.read_revenue(), "-62000")

    def test_mismatched_approval_id_is_rejected(self):
        self.write_approval("APPROVED")

        result = self.run_fix(approval_id="WRONG-ID")

        self.assertEqual(result["status"], "REJECTED")
        self.assertEqual(self.read_revenue(), "-62000")

    def test_mismatched_replacement_amount_is_rejected(self):
        self.write_approval("APPROVED")

        result = self.run_fix(replacement=63000)

        self.assertEqual(result["status"], "REJECTED")
        self.assertEqual(self.read_revenue(), "-62000")

    def test_consumed_approval_is_rejected(self):
        self.write_approval("CONSUMED")

        result = self.run_fix()

        self.assertEqual(result["status"], "REJECTED")
        self.assertEqual(self.read_revenue(), "-62000")

    def test_valid_approval_allows_remediation(self):
        self.write_approval("APPROVED")

        result = self.run_fix()

        self.assertEqual(result["status"], "FIXED")
        self.assertEqual(result["approval_id"], "TEST-001")
        self.assertEqual(self.read_revenue(), "62000")
     
    def test_mismatched_approver_is_rejected(self):
        """A different approver identity must not authorize a repair."""

        self.write_approval("APPROVED")

        result = self.run_fix(
            approved_by="Impersonator"
        )

        self.assertEqual(result["status"], "REJECTED")
        self.assertEqual(self.read_revenue(), "-62000")

    def test_mismatched_approval_timestamp_is_rejected(self):
        """The timestamp must match the approval registry."""

        self.write_approval("APPROVED")

        result = self.run_fix(
            approved_at="2025-01-01T00:00:00"
        )

        self.assertEqual(result["status"], "REJECTED")
        self.assertEqual(self.read_revenue(), "-62000")

if __name__ == "__main__":
    unittest.main(verbosity=2)