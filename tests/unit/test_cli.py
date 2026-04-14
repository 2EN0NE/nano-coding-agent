import importlib
import os
import stat
import subprocess
import tempfile
import unittest
import unittest.mock as mock
from pathlib import Path

from click.testing import CliRunner
from nano_coding.skills.guard import confirm_principles, install, update, validate


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

            dest_principles = root / ".nano-coding-agent" / "principles" / "core.md"
            self.assertTrue(dest_principles.exists())


class TestCliValidate(unittest.TestCase):
    def test_validate_success_exits_0(self) -> None:
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "AGENTS.md").write_text("# Project\n\n## 基础原则\nSome rules.\n")
            (root / "BACKGROUND.md").write_text("# Background\nProject vision.\n")
            (root / "BANNED-AGENT-BEHAVIORS.md").write_text(
                "# Banned behaviors\nDon't do X.\n"
            )
            pre_commit = root / ".git" / "hooks" / "pre-commit"
            pre_commit.parent.mkdir(parents=True)
            pre_commit.write_text("#!/bin/bash\necho hook\n")
            pre_commit.chmod(pre_commit.stat().st_mode | stat.S_IXUSR)
            (root / "tests" / "unit").mkdir(parents=True)
            (root / "tests" / "integration").mkdir()
            (root / "tests" / "unit" / "dummy.py").write_text("pass\n")
            (root / "README.md").write_text("# Project\n\nRun tests: `pytest -v`\n")

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


class TestCliRootSkills(unittest.TestCase):
    def _reload_cli_module(self, mock_find):
        with (
            mock.patch(
                "nano_coding.core.project_discovery.find_nearest_agent_dir", mock_find
            ),
            mock.patch("nano_coding.core.version_checker.check_version"),
        ):
            import nano_coding.cli

            importlib.reload(nano_coding.cli)
            return nano_coding.cli.cli

    def test_local_skill_appears_in_help(self) -> None:
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as tmp:
            agent_dir = Path(tmp) / ".nano-coding-agent"
            skills_dir = agent_dir / "skills" / "hello"
            skills_dir.mkdir(parents=True)
            (skills_dir / "SKILL.md").write_text(
                "---\nname: hello\n---\nHello world skill body\n"
            )

            def mock_find(start_dir):
                return agent_dir

            cli = self._reload_cli_module(mock_find)
            result = runner.invoke(cli, ["--help"])
            self.assertEqual(result.exit_code, 0)
            self.assertIn("hello", result.output)

    def test_local_skill_overrides_builtin(self) -> None:
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as tmp:
            agent_dir = Path(tmp) / ".nano-coding-agent"
            skills_dir = agent_dir / "skills" / "guard"
            skills_dir.mkdir(parents=True)
            (skills_dir / "SKILL.md").write_text(
                "---\nname: guard\n---\nOverridden guard skill\n"
            )

            def mock_find(start_dir):
                return agent_dir

            cli = self._reload_cli_module(mock_find)
            result = runner.invoke(cli, ["guard"])
            self.assertEqual(result.exit_code, 0)
            self.assertIn("Overridden guard skill", result.output)

    def test_local_python_skill_loaded(self) -> None:
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as tmp:
            agent_dir = Path(tmp) / ".nano-coding-agent"
            skills_dir = agent_dir / "skills" / "pyhello"
            skills_dir.mkdir(parents=True)
            (skills_dir / "SKILL.md").write_text(
                "---\nname: pyhello\nentrypoint: main:hello\n---\nPython hello skill\n"
            )
            (skills_dir / "main.py").write_text(
                "import click\n\n@click.command()\ndef hello():\n    click.echo('hello from python skill')\n"
            )

            def mock_find(start_dir):
                return agent_dir

            cli = self._reload_cli_module(mock_find)
            result = runner.invoke(cli, ["pyhello"])
            self.assertEqual(result.exit_code, 0)
            self.assertIn("hello from python skill", result.output)

    def test_no_agent_dir_backwards_compatible(self) -> None:
        runner = CliRunner()

        def mock_find(start_dir):
            return None

        cli = self._reload_cli_module(mock_find)
        result = runner.invoke(cli, ["--help"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("install", result.output)
        self.assertIn("validate", result.output)
        self.assertIn("update", result.output)
        self.assertIn("scan", result.output)
        self.assertIn("principle-review", result.output)


class TestCliConfirmPrinciples(unittest.TestCase):
    """Tests for confirm-principles CLI command."""

    def _init_git(self, root: Path) -> None:
        subprocess.run(
            ["git", "init"],
            cwd=str(root),
            capture_output=True,
            check=False,
        )
        subprocess.run(
            ["git", "config", "user.email", "test@test.com"],
            cwd=str(root),
            capture_output=True,
            check=False,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test"],
            cwd=str(root),
            capture_output=True,
            check=False,
        )

    def test_no_protected_docs_staged(self) -> None:
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._init_git(root)
            result = runner.invoke(confirm_principles, ["--path", str(root)])
            self.assertEqual(result.exit_code, 0)
            self.assertEqual(result.output.strip(), "")

    def test_protected_doc_staged_yes_flag(self) -> None:
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._init_git(root)
            (root / "AGENTS.md").write_text("# Project\n")
            subprocess.run(
                ["git", "add", "AGENTS.md"],
                cwd=str(root),
                capture_output=True,
                check=False,
            )
            result = runner.invoke(confirm_principles, ["--path", str(root), "--yes"])
            self.assertEqual(result.exit_code, 0)
            self.assertIn(
                "Changes to protected documents confirmed via --yes", result.output
            )
            self.assertIn("AGENTS.md", result.output)

    def test_protected_doc_staged_interactive_yes(self) -> None:
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._init_git(root)
            (root / "AGENTS.md").write_text("# Project\n")
            subprocess.run(
                ["git", "add", "AGENTS.md"],
                cwd=str(root),
                capture_output=True,
                check=False,
            )
            result = runner.invoke(
                confirm_principles, ["--path", str(root)], input="yes\n"
            )
            self.assertEqual(result.exit_code, 0)

    def test_protected_doc_staged_interactive_no(self) -> None:
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._init_git(root)
            (root / "AGENTS.md").write_text("# Project\n")
            subprocess.run(
                ["git", "add", "AGENTS.md"],
                cwd=str(root),
                capture_output=True,
                check=False,
            )
            result = runner.invoke(
                confirm_principles, ["--path", str(root)], input="no\n"
            )
            self.assertEqual(result.exit_code, 1)
            self.assertIn("Aborting commit", result.output)
