"""Unit tests for nano_coding.core.validator."""

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
            self.assertIn(
                "No tests directory or test files detected.", result["warnings"]
            )

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


class TestValidatorAgentsAbort(unittest.TestCase):
    """Tests for AGENTS_ABORT.md / BANNED-AGENT-BEHAVIORS.md validation."""

    def _create_base_project(self, root: Path) -> None:
        """Create base valid project structure to satisfy other checks."""
        (root / "AGENTS.md").write_text("# Project\n\n## 基础原则\nSome rules.\n")
        pre_commit = root / ".git" / "hooks" / "pre-commit"
        pre_commit.parent.mkdir(parents=True)
        pre_commit.write_text("#!/bin/bash\necho hook\n")
        pre_commit.chmod(pre_commit.stat().st_mode | stat.S_IXUSR)
        (root / "tests").mkdir()

    def test_agents_abort_exists_success(self) -> None:
        """AGENTS_ABORT.md exists -> success."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._create_base_project(root)
            (root / "AGENTS_ABORT.md").write_text("# Banned behaviors\n")

            result = validate_project(str(root), check_agents_abort=True)
            self.assertTrue(result["success"])

    def test_banned_behaviors_exists_success(self) -> None:
        """BANNED-AGENT-BEHAVIORS.md exists -> success."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._create_base_project(root)
            (root / "BANNED-AGENT-BEHAVIORS.md").write_text("# Banned behaviors\n")

            result = validate_project(str(root), check_agents_abort=True)
            self.assertTrue(result["success"])

    def test_both_exist_success(self) -> None:
        """Both AGENTS_ABORT.md and BANNED-AGENT-BEHAVIORS.md exist -> success."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._create_base_project(root)
            (root / "AGENTS_ABORT.md").write_text("# Banned behaviors\n")
            (root / "BANNED-AGENT-BEHAVIORS.md").write_text("# Banned behaviors\n")

            result = validate_project(str(root), check_agents_abort=True)
            self.assertTrue(result["success"])

    def test_neither_exists_fails(self) -> None:
        """Both files missing -> blocking error."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._create_base_project(root)

            result = validate_project(str(root), check_agents_abort=True)
            self.assertFalse(result["success"])
            self.assertTrue(
                any(
                    "AGENTS_ABORT" in msg or "BANNED" in msg
                    for msg in result["blocking"]
                ),
                f"Expected AGENTS_ABORT/BANNED error, got {result}",
            )

    def test_empty_file_fails(self) -> None:
        """File exists but empty -> blocking error."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._create_base_project(root)
            (root / "AGENTS_ABORT.md").write_text("")

            result = validate_project(str(root), check_agents_abort=True)
            self.assertFalse(result["success"])
            self.assertTrue(
                any("empty" in msg.lower() for msg in result["blocking"]),
                f"Expected empty file error, got {result}",
            )

    def test_disabled_does_not_check(self) -> None:
        """check_agents_abort=False -> no error even if missing."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._create_base_project(root)

            result = validate_project(str(root), check_agents_abort=False)
            self.assertTrue(result["success"])
            self.assertFalse(
                any(
                    "AGENTS_ABORT" in msg or "BANNED" in msg
                    for msg in result["blocking"]
                ),
            )


class TestValidatorBackground(unittest.TestCase):
    """Tests for BACKGROUND.md validation."""

    def _create_base_project(self, root: Path) -> None:
        """Create base valid project structure to satisfy other checks."""
        (root / "AGENTS.md").write_text("# Project\n\n## 基础原则\nSome rules.\n")
        pre_commit = root / ".git" / "hooks" / "pre-commit"
        pre_commit.parent.mkdir(parents=True)
        pre_commit.write_text("#!/bin/bash\necho hook\n")
        pre_commit.chmod(pre_commit.stat().st_mode | stat.S_IXUSR)
        (root / "tests").mkdir()

    def test_background_exists_success(self) -> None:
        """BACKGROUND.md exists -> success."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._create_base_project(root)
            (root / "BACKGROUND.md").write_text("# Background\nProject context.\n")

            result = validate_project(str(root), check_background=True)
            self.assertTrue(result["success"])

    def test_background_missing_fails(self) -> None:
        """BACKGROUND.md missing -> blocking error."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._create_base_project(root)

            result = validate_project(str(root), check_background=True)
            self.assertFalse(result["success"])
            self.assertTrue(
                any("BACKGROUND" in msg for msg in result["blocking"]),
                f"Expected BACKGROUND.md error, got {result}",
            )

    def test_disabled_does_not_check(self) -> None:
        """check_background=False -> no error even if missing."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._create_base_project(root)

            result = validate_project(str(root), check_background=False)
            self.assertTrue(result["success"])
            self.assertFalse(
                any("BACKGROUND" in msg for msg in result["blocking"]),
            )


class TestValidatorTestSeparation(unittest.TestCase):
    """Tests for test directory separation validation."""

    def _create_base_project(self, root: Path) -> None:
        """Create base valid project structure to satisfy other checks."""
        (root / "AGENTS.md").write_text("# Project\n\n## 基础原则\nSome rules.\n")
        pre_commit = root / ".git" / "hooks" / "pre-commit"
        pre_commit.parent.mkdir(parents=True)
        pre_commit.write_text("#!/bin/bash\necho hook\n")
        pre_commit.chmod(pre_commit.stat().st_mode | stat.S_IXUSR)

    def test_both_dirs_exist_success(self) -> None:
        """tests/unit/ and tests/integration/ exist -> success."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._create_base_project(root)
            (root / "tests" / "unit").mkdir(parents=True)
            (root / "tests" / "integration").mkdir()

            result = validate_project(str(root), check_test_separation=True)
            self.assertTrue(result["success"])

    def test_missing_unit_fails(self) -> None:
        """Missing tests/unit/ -> blocking error."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._create_base_project(root)
            (root / "tests").mkdir()
            (root / "tests" / "integration").mkdir()

            result = validate_project(str(root), check_test_separation=True)
            self.assertFalse(result["success"])
            self.assertTrue(
                any("unit" in msg.lower() for msg in result["blocking"]),
                f"Expected tests/unit/ error, got {result}",
            )

    def test_missing_integration_fails(self) -> None:
        """Missing tests/integration/ -> blocking error."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._create_base_project(root)
            (root / "tests").mkdir()
            (root / "tests" / "unit").mkdir()

            result = validate_project(str(root), check_test_separation=True)
            self.assertFalse(result["success"])
            self.assertTrue(
                any("integration" in msg.lower() for msg in result["blocking"]),
                f"Expected tests/integration/ error, got {result}",
            )

    def test_no_tests_dir_fails(self) -> None:
        """No tests/ dir -> blocking error."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._create_base_project(root)

            result = validate_project(str(root), check_test_separation=True)
            self.assertFalse(result["success"])
            self.assertTrue(
                any("tests" in msg.lower() for msg in result["blocking"]),
                f"Expected tests/ error, got {result}",
            )

    def test_disabled_does_not_check(self) -> None:
        """check_test_separation=False -> no error even if missing."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._create_base_project(root)

            result = validate_project(str(root), check_test_separation=False)
            self.assertTrue(result["success"])
            self.assertFalse(
                any(
                    "unit" in msg.lower() or "integration" in msg.lower()
                    for msg in result["blocking"]
                ),
            )


class TestValidatorTestCommands(unittest.TestCase):
    """Tests for test commands validation in README.md / AGENTS.md."""

    def _create_base_project(self, root: Path) -> None:
        """Create base valid project structure to satisfy other checks."""
        pre_commit = root / ".git" / "hooks" / "pre-commit"
        pre_commit.parent.mkdir(parents=True)
        pre_commit.write_text("#!/bin/bash\necho hook\n")
        pre_commit.chmod(pre_commit.stat().st_mode | stat.S_IXUSR)
        (root / "tests").mkdir()

    def test_readme_has_command_success(self) -> None:
        """README.md contains 'pytest -v' -> success."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._create_base_project(root)
            (root / "AGENTS.md").write_text("# Project\n\n## 基础原则\nSome rules.\n")
            (root / "README.md").write_text(
                "# Project\n\nRun tests with: `pytest -v`\n"
            )

            result = validate_project(str(root), check_test_commands=True)
            self.assertTrue(result["success"])

    def test_agents_has_command_success(self) -> None:
        """AGENTS.md contains 'npm test' -> success."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._create_base_project(root)
            (root / "AGENTS.md").write_text(
                "# Project\n\n## 基础原则\nRun tests: `npm test`\n"
            )

            result = validate_project(str(root), check_test_commands=True)
            self.assertTrue(result["success"])

    def test_neither_has_command_fails(self) -> None:
        """Neither README.md nor AGENTS.md has test command -> blocking error."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._create_base_project(root)
            (root / "AGENTS.md").write_text("# Project\n\n## 基础原则\nSome rules.\n")
            (root / "README.md").write_text("# Project\n\nNo test info here.\n")

            result = validate_project(str(root), check_test_commands=True)
            self.assertFalse(result["success"])
            self.assertTrue(
                any(
                    "test command" in msg.lower()
                    or "pytest" in msg.lower()
                    or "npm test" in msg.lower()
                    for msg in result["blocking"]
                ),
                f"Expected test command error, got {result}",
            )

    def test_vague_command_fails(self) -> None:
        """Only '运行测试' without specific command -> blocking error."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._create_base_project(root)
            (root / "AGENTS.md").write_text(
                "# Project\n\n## 基础原则\n运行测试\nSome rules.\n"
            )
            (root / "README.md").write_text("# Project\n\n运行测试\n")

            result = validate_project(str(root), check_test_commands=True)
            self.assertFalse(result["success"])
            self.assertTrue(
                any(
                    "specific" in msg.lower()
                    or "vague" in msg.lower()
                    or "command" in msg.lower()
                    for msg in result["blocking"]
                ),
                f"Expected specific command error, got {result}",
            )

    def test_disabled_does_not_check(self) -> None:
        """check_test_commands=False -> no error even if missing."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._create_base_project(root)
            (root / "AGENTS.md").write_text("# Project\n\n## 基础原则\nSome rules.\n")

            result = validate_project(str(root), check_test_commands=False)
            self.assertTrue(result["success"])
            self.assertFalse(
                any("test command" in msg.lower() for msg in result["blocking"]),
            )


if __name__ == "__main__":
    unittest.main()
