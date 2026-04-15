"""Principle-review skill integration tests.

These tests run the principle-review commands against the actual nano-coding-agent
repository to verify they work on a real project.

TESTED_COMMANDS declaration for coverage tracking:
- ("principle-review",)
"""

from click.testing import CliRunner

from nano_coding.cli import cli as root_cli

TESTED_COMMANDS = [
    ("principle-review",),
]


def test_length_limit_on_real_project() -> None:
    runner = CliRunner()
    result = runner.invoke(root_cli, ["principle-review", "--length-limit", "."])

    assert result.exit_code == 0, f"Length limit check failed. Output:\n{result.output}"

    assert "OK" in result.output


def test_separate_concerns_on_real_project() -> None:
    runner = CliRunner()
    result = runner.invoke(root_cli, ["principle-review", "--separate-concerns", "."])

    assert result.exit_code in [0, 1], f"Unexpected exit code. Output:\n{result.output}"


def test_check_changes_runs_without_crash() -> None:
    runner = CliRunner()
    result = runner.invoke(root_cli, ["principle-review", "--check-changes", "."])

    assert result.exit_code in [0, 1], f"Unexpected exit code. Output:\n{result.output}"

    assert "Traceback" not in result.output
    assert "Exception" not in result.output


def test_all_checks_together() -> None:
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

    assert result.exit_code in [0, 1], f"Unexpected exit code. Output:\n{result.output}"

    assert "Traceback" not in result.output
