
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

import first_llm


def make_tool_call(name, arguments="{}"):
    return SimpleNamespace(
        name=name,
        arguments=arguments,
    )


class TestWriteGuardrails(unittest.TestCase):

    def test_direct_write_tool_is_blocked(self):
        """Low-level write tools must not execute directly."""

        mock_fix = Mock(
            return_value={"status": "SHOULD_NOT_RUN"}
        )

        with patch.dict(
            first_llm.tool_functions,
            {"fix_negative_revenue": mock_fix},
        ):
            result = first_llm.execute_tool(
                make_tool_call(
                    "fix_negative_revenue",
                    '{"customer": "Globex"}',
                )
            )

        self.assertEqual(
            result["status"],
            "WRITE_TOOL_BLOCKED",
        )

        mock_fix.assert_not_called()

    def test_unknown_tool_is_blocked(self):
        """Unknown tools must never be executed."""

        result = first_llm.execute_tool(
            make_tool_call("unknown_dangerous_tool")
        )

        self.assertEqual(
            result["status"],
            "TOOL_BLOCKED",
        )

    def test_controlled_workflow_path_is_allowed(self):
        """The controlled workflow route passes the guardrail.

        The real workflow is replaced by a mock, so no data changes.
        """

        mock_workflow = Mock(
            return_value={"status": "MOCK_WORKFLOW"}
        )

        with (
            patch.dict(
                first_llm.tool_functions,
                {"run_quality_workflow": mock_workflow},
            ),
            patch("first_llm.update_memory_context") as mock_memory,
        ):
            result = first_llm.execute_tool(
                make_tool_call("run_quality_workflow")
            )

        self.assertEqual(
            result["status"],
            "MOCK_WORKFLOW",
        )

        mock_workflow.assert_called_once_with()
        mock_memory.assert_called_once()


if __name__ == "__main__":
    unittest.main(verbosity=2)