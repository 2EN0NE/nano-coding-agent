"""Integration tests for scan command with CheckEngine refactor."""

import stat
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from nano_coding.skills.guard import scan

TESTED_COMMANDS = [
    ("scan",),
    ("scan", "scan --interactive"),
    ("scan", "scan --staged"),
]


class TestScanIntegration(unittest.TestCase):
    """Integration tests for scan with new flags."""

    def _create_minimal_project(self, root: Path) -> None:
        (root / "AGENTS.md").write_text("# Project\n\n## 基础原则\nSome rules.\n")
        pre_commit = root / ".git" / "hooks" / "pre-commit"
        pre_commit.parent.mkdir(parents=True)
        pre_commit.write_text("#!/bin/bash\necho hook\n")
        pre_commit.chmod(pre_commit.stat().st_mode | stat.S_IXUSR)
        (root / "tests").mkdir()
        (root / "tests" / "dummy.py").write_text("pass\n")

    def test_scan_runs_and_outputs_summary(self) -> None:
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._create_minimal_project(root)
            result = runner.invoke(scan, ["--path", str(root)])
            self.assertIn(
                result.exit_code,
                [0, 1],
                msg=f"Unexpected exit code. Output:\n{result.output}",
            )
            self.assertIn("SUMMARY", result.output)
            self.assertNotIn("Traceback", result.output)

    def test_scan_interactive_runs_without_crash(self) -> None:
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._create_minimal_project(root)
            with patch(
                "nano_coding.skills.guard.show_report_interactively"
            ) as mock_show:
                result = runner.invoke(scan, ["--path", str(root), "--interactive"])
                self.assertIn(
                    result.exit_code,
                    [0, 1],
                    msg=f"Unexpected exit code. Output:\n{result.output}",
                )
                self.assertNotIn("Traceback", result.output)
                mock_show.assert_called_once()
                self.assertIn("SUMMARY", mock_show.call_args[0][0])

    def test_scan_staged_runs_without_crash(self) -> None:
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._create_minimal_project(root)
            result = runner.invoke(scan, ["--path", str(root), "--staged"])
            self.assertIn(
                result.exit_code,
                [0, 1],
                msg=f"Unexpected exit code. Output:\n{result.output}",
            )
            self.assertIn("SUMMARY", result.output)
            self.assertNotIn("Traceback", result.output)


if __name__ == "__main__":
    unittest.main()
