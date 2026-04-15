"""Integration tests for scan command with CheckEngine refactor."""

import stat
import tempfile
from pathlib import Path

from click.testing import CliRunner

from nano_coding.skills.guard import scan

TESTED_COMMANDS = [
    ("scan",),
    ("scan", "scan --interactive"),
    ("scan", "scan --staged"),
]


def _create_minimal_project(root: Path) -> None:
    (root / "AGENTS.md").write_text("# Project\n\n## 基础原则\nSome rules.\n")
    pre_commit = root / ".git" / "hooks" / "pre-commit"
    pre_commit.parent.mkdir(parents=True)
    pre_commit.write_text("#!/bin/bash\necho hook\n")
    pre_commit.chmod(pre_commit.stat().st_mode | stat.S_IXUSR)
    (root / "tests").mkdir()
    (root / "tests" / "dummy.py").write_text("pass\n")


def test_scan_runs_and_outputs_summary() -> None:
    runner = CliRunner()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _create_minimal_project(root)
        result = runner.invoke(scan, ["--path", str(root)])
        assert result.exit_code in [0, 1], (
            f"Unexpected exit code. Output:\n{result.output}"
        )
        assert "SUMMARY" in result.output
        assert "Traceback" not in result.output


def test_scan_interactive_runs_without_crash(monkeypatch) -> None:
    runner = CliRunner()
    calls = []

    def fake_show(report):
        calls.append(report)

    monkeypatch.setattr("nano_coding.skills.guard.show_report_interactively", fake_show)

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _create_minimal_project(root)
        result = runner.invoke(scan, ["--path", str(root), "--interactive"])
        assert result.exit_code in [0, 1], (
            f"Unexpected exit code. Output:\n{result.output}"
        )
        assert "Traceback" not in result.output
        assert len(calls) == 1
        assert "SUMMARY" in calls[0]


def test_scan_staged_runs_without_crash() -> None:
    runner = CliRunner()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _create_minimal_project(root)
        result = runner.invoke(scan, ["--path", str(root), "--staged"])
        assert result.exit_code in [0, 1], (
            f"Unexpected exit code. Output:\n{result.output}"
        )
        assert "SUMMARY" in result.output
        assert "Traceback" not in result.output
