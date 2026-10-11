
import unittest
from unittest.mock import patch

import first_llm


def make_test_memory(active_customer="Acme", messages=None):
    """Create isolated test data; do not use real customer files."""

    customers = {
        "Globex": {"current_revenue": 62000},
        "Acme": {"current_revenue": 85000},
        "Initech": {"current_revenue": 91000},
        "Umbrella": {"current_revenue": 47000},
    }

    if messages is None:
        messages = []

    return {
        "version": 2,
        "messages": messages,
        "summary": "",
        "memory_context": {
            "active_customer": active_customer,
            "last_topic": None,
            "last_tool": None,
            "last_approval_id": None,
            "last_workflow_status": None,
            "last_business_snapshot": None,
            "customers": customers,
        },
    }


class TestRelevantMemory(unittest.TestCase):

    def test_explicit_customer(self):
        """A named customer should be selected directly."""

        with patch(
            "first_llm.load_conversation_memory",
            return_value=make_test_memory(),
        ):
            result = first_llm.find_relevant_memory(
                "What do you remember about Globex?"
            )

        self.assertEqual(result["status"], "OK")
        self.assertEqual(result["match_type"], "EXPLICIT_CUSTOMER")
        self.assertEqual(result["customer"], "Globex")

    def test_indirect_reference_uses_active_customer(self):
        """An indirect reference should use the active customer."""

        with patch(
            "first_llm.load_conversation_memory",
            return_value=make_test_memory(active_customer="Acme"),
        ):
            result = first_llm.find_relevant_memory(
                "What do you remember about that customer?"
            )

        self.assertEqual(result["status"], "OK")
        self.assertEqual(result["match_type"], "ACTIVE_CUSTOMER")
        self.assertEqual(result["customer"], "Acme")

    def test_other_customer_is_ambiguous(self):
        """The agent must not guess which other customer is meant."""

        with patch(
            "first_llm.load_conversation_memory",
            return_value=make_test_memory(active_customer="Acme"),
        ):
            result = first_llm.find_relevant_memory(
                "What do you remember about the other customer?"
            )

        self.assertEqual(result["status"], "AMBIGUOUS")
        self.assertEqual(result["match_type"], "AMBIGUOUS_REFERENCE")
        self.assertIsNone(result["customer"])
        self.assertCountEqual(
            result["candidates"],
            ["Globex", "Initech", "Umbrella"],
        )

    def test_no_match_returns_not_found(self):
        """Without a customer or useful context, do not invent a match."""

        with patch(
            "first_llm.load_conversation_memory",
            return_value=make_test_memory(
                active_customer=None,
                messages=[],
            ),
        ):
            result = first_llm.find_relevant_memory(
                "Tell me about the revenue."
            )

        self.assertEqual(result["status"], "NOT_FOUND")
        self.assertIsNone(result["customer"])


if __name__ == "__main__":
    unittest.main(verbosity=2)