"""Principle-review skill integration tests.

These tests run the principle-review commands against the actual nano-coding-agent
repository to verify they work on a real project.

TESTED_COMMANDS declaration for coverage tracking:
- ("principle-review",)
"""

import unittest

from click.testing import CliRunner

from nano_coding.cli import cli as root_cli

TESTED_COMMANDS = [
    ("principle-review",),
]


class TestPrincipleReviewLengthLimitIntegration(unittest.TestCase):
    def test_length_limit_on_real_project(self) -> None:
        runner = CliRunner()
        result = runner.invoke(root_cli, ["principle-review", "--length-limit", "."])

        self.assertEqual(
            result.exit_code,
            0,
            msg=f"Length limit check failed. Output:\n{result.output}",
        )

        self.assertIn("OK", result.output)


class TestPrincipleReviewSeparateConcernsIntegration(unittest.TestCase):
    def test_separate_concerns_on_real_project(self) -> None:
        runner = CliRunner()
        result = runner.invoke(
            root_cli, ["principle-review", "--separate-concerns", "."]
        )

        self.assertIn(
            result.exit_code,
            [0, 1],
            msg=f"Unexpected exit code. Output:\n{result.output}",
        )


class TestPrincipleReviewCheckChangesIntegration(unittest.TestCase):
    def test_check_changes_runs_without_crash(self) -> None:
        runner = CliRunner()
        result = runner.invoke(root_cli, ["principle-review", "--check-changes", "."])

        self.assertIn(
            result.exit_code,
            [0, 1],
            msg=f"Unexpected exit code. Output:\n{result.output}",
        )

        self.assertNotIn("Traceback", result.output)
        self.assertNotIn("Exception", result.output)


class TestPrincipleReviewCombinedIntegration(unittest.TestCase):
    def test_all_checks_together(self) -> None:
        runner = CliRunner()
        result = runner.invoke(
            root_cli,
            [
                "principle-review",
                "--length-limit",
                "--separate-concerns",
                "--check-changes",
                ".",
            ],
        )

        self.assertIn(
            result.exit_code,
            [0, 1],
            msg=f"Unexpected exit code. Output:\n{result.output}",
        )

        self.assertNotIn("Traceback", result.output)


if __name__ == "__main__":
    unittest.main()
