import os
import stat
import tempfile
import unittest
from pathlib import Path

from click.testing import CliRunner
from nano_coding.skills.guard import install, update, validate


class TestCliInstall(unittest.TestCase):
    def test_install_non_git_fails(self) -> None:
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as tmp:
            result = runner.invoke(install, [tmp])
            self.assertEqual(result.exit_code, 1)

    def test_install_git_directory_copies_hook_and_principles(self) -> None:
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            git_dir = root / ".git"
            git_dir.mkdir()

            result = runner.invoke(install, [str(root)])
            self.assertEqual(result.exit_code, 0)

            dest_hook = git_dir / "hooks" / "pre-commit"
            self.assertTrue(dest_hook.exists())
            self.assertTrue(os.access(dest_hook, os.X_OK))

            dest_principles = root / "principles" / "core.md"
            self.assertTrue(dest_principles.exists())


class TestCliValidate(unittest.TestCase):
    def test_validate_success_exits_0(self) -> None:
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "AGENTS.md").write_text("# Project\n\n## 基础原则\nSome rules.\n")
            pre_commit = root / ".git" / "hooks" / "pre-commit"
            pre_commit.parent.mkdir(parents=True)
            pre_commit.write_text("#!/bin/bash\necho hook\n")
            pre_commit.chmod(pre_commit.stat().st_mode | stat.S_IXUSR)
            (root / "tests").mkdir()
            (root / "tests" / "dummy.py").write_text("pass\n")

            result = runner.invoke(validate, [str(root)])
            self.assertEqual(result.exit_code, 0)

    def test_validate_blocking_exits_1(self) -> None:
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            result = runner.invoke(validate, [str(root)])
            self.assertEqual(result.exit_code, 1)

    def test_validate_with_new_options(self) -> None:
        """Test that validate accepts new --check-* options."""
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            # Create minimal valid project structure
            (root / "AGENTS.md").write_text("# Project\n\n## 基础原则\nSome rules.\n")
            (root / "BACKGROUND.md").write_text("# Background\nProject vision.\n")
            (root / "BANNED-AGENT-BEHAVIORS.md").write_text(
                "# Banned behaviors\nDon't do X.\n"
            )
            pre_commit = root / ".git" / "hooks" / "pre-commit"
            pre_commit.parent.mkdir(parents=True)
            pre_commit.write_text("#!/bin/bash\necho hook\n")
            pre_commit.chmod(pre_commit.stat().st_mode | stat.S_IXUSR)
            # Create tests directories
            (root / "tests" / "unit").mkdir(parents=True)
            (root / "tests" / "integration").mkdir(parents=True)
            (root / "tests" / "unit" / "dummy.py").write_text("pass\n")
            # README with test command
            (root / "README.md").write_text("# Project\n\nRun tests: `pytest -v`\n")

            result = runner.invoke(
                validate,
                [
                    str(root),
                    "--check-agents-abort",
                    "--check-background",
                    "--check-test-separation",
                    "--check-test-commands",
                ],
            )
            self.assertEqual(result.exit_code, 0, msg=result.output)


class TestCliUpdate(unittest.TestCase):
    def test_update_idempotency(self) -> None:
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            principles_dir = root / "principles"
            principles_dir.mkdir()
            principles_file = principles_dir / "core.md"
            target_file = root / "AGENTS.md"

            principles_file.write_text("### Principle A\nBody A\n")
            target_file.write_text(
                "# Agents\n\n## 基础原则\n### Principle A\nOld Body\n"
            )

            result = runner.invoke(update, [str(root)])
            self.assertEqual(result.exit_code, 0)
            first_result = target_file.read_text()

            result = runner.invoke(update, [str(root)])
            self.assertEqual(result.exit_code, 0)
            second_result = target_file.read_text()

            self.assertEqual(first_result, second_result)
