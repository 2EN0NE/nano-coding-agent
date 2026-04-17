"""Unit tests for guardian.core.validator."""

import os
import stat
import tempfile
import unittest
from pathlib import Path

from nano_coding.core.validator import validate_project


class TestValidator(unittest.TestCase):
    """Tests for validate_project function."""

    def _create_valid_project(self, root: Path) -> None:
        """Create a minimal valid project structure in root."""
        # AGENTS.md with required section
        (root / "AGENTS.md").write_text("# Project\n\n## 基础原则\nSome rules.\n")

        # .git/hooks/pre-commit executable
        pre_commit = root / ".git" / "hooks" / "pre-commit"
        pre_commit.parent.mkdir(parents=True)
        pre_commit.write_text("#!/bin/bash\necho hook\n")
        pre_commit.chmod(pre_commit.stat().st_mode | stat.S_IXUSR)

        # tests directory
        (root / "tests").mkdir()
        (root / "tests" / "dummy.py").write_text("pass\n")

    def test_valid_project_passes(self) -> None:
        """A correctly structured temp project should pass."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._create_valid_project(root)
            result = validate_project(str(root))
            self.assertTrue(result["success"])
            self.assertEqual(result["blocking"], [])
            self.assertEqual(result["warnings"], [])

    def test_missing_agents_md_fails(self) -> None:
        """Missing AGENTS.md should produce a blocking error."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            # Create everything except AGENTS.md
            pre_commit = root / ".git" / "hooks" / "pre-commit"
            pre_commit.parent.mkdir(parents=True)
            pre_commit.write_text("#!/bin/bash\necho hook\n")
            pre_commit.chmod(pre_commit.stat().st_mode | stat.S_IXUSR)
            (root / "tests").mkdir()

            result = validate_project(str(root))
            self.assertFalse(result["success"])
            self.assertIn("AGENTS.md not found in project root.", result["blocking"])

    def test_missing_jichu_yuanze_fails(self) -> None:
        """AGENTS.md without ## 基础原则 should produce a blocking error."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            # AGENTS.md without required section
            (root / "AGENTS.md").write_text("# Project\n\nSome other content.\n")

            pre_commit = root / ".git" / "hooks" / "pre-commit"
            pre_commit.parent.mkdir(parents=True)
            pre_commit.write_text("#!/bin/bash\necho hook\n")
            pre_commit.chmod(pre_commit.stat().st_mode | stat.S_IXUSR)
            (root / "tests").mkdir()

            result = validate_project(str(root))
            self.assertFalse(result["success"])
            self.assertIn(
                'AGENTS.md is missing the required "## 基础原则" section.',
                result["blocking"],
            )

    def test_file_exceeds_max_lines_fails(self) -> None:
        """A tracked source file exceeding max_lines should be blocking."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._create_valid_project(root)
            long_file = root / "long.py"
            long_file.write_text("\n".join([f"line {i}" for i in range(1001)]))

            result = validate_project(str(root))
            self.assertFalse(result["success"])
            self.assertTrue(
                any("exceeds 1000 lines" in msg for msg in result["blocking"]),
                f"Expected line-count blocking error, got {result}",
            )

    def test_no_tests_warns(self) -> None:
        """Absence of tests directory/files should produce a warning."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "AGENTS.md").write_text("# Project\n\n## 基础原则\nSome rules.\n")
            pre_commit = root / ".git" / "hooks" / "pre-commit"
            pre_commit.parent.mkdir(parents=True)
            pre_commit.write_text("#!/bin/bash\necho hook\n")
            pre_commit.chmod(pre_commit.stat().st_mode | stat.S_IXUSR)
            # intentionally no tests

            result = validate_project(str(root))
            self.assertTrue(result["success"])
            self.assertIn("No tests directory or test files detected.", result["warnings"])

    def test_check_forbidden_dirs_flag(self) -> None:
        """Forbidden dirs check should be toggleable via check_forbidden_dirs flag."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._create_valid_project(root)
            (root / "templates").mkdir()

            result_with = validate_project(str(root), check_forbidden_dirs=True)
            self.assertFalse(result_with["success"])
            self.assertTrue(
                any("Forbidden directory" in msg for msg in result_with["blocking"]),
                f"Expected forbidden dir error, got {result_with}",
            )

            result_without = validate_project(str(root), check_forbidden_dirs=False)
            self.assertTrue(result_without["success"])
            self.assertFalse(
                any("Forbidden directory" in msg for msg in result_without["blocking"]),
            )


if __name__ == "__main__":
    unittest.main()
