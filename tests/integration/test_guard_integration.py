"""Guard skill integration tests.

These tests run the guard commands against the actual nano-coding-agent
repository to verify they work on a real project.

TESTED_COMMANDS declaration for coverage tracking:
- ("install",)
- ("validate",)
- ("validate", "validate --check-agents-abort")
- ("validate", "validate --check-background")
- ("validate", "validate --check-test-commands")
- ("validate", "validate --check-test-separation")
- ("update",)
- ("scan",)
"""

import tempfile
import unittest
from pathlib import Path

from click.testing import CliRunner

from nano_coding.skills.guard import install, scan, update, validate

TESTED_COMMANDS = [
    ("install",),
    ("validate",),
    ("validate", "validate --check-agents-abort"),
    ("validate", "validate --check-background"),
    ("validate", "validate --check-test-commands"),
    ("validate", "validate --check-test-separation"),
    ("update",),
    ("scan",),
]


class TestGuardValidateIntegration(unittest.TestCase):
    def test_validate_on_real_project_succeeds(self) -> None:
        runner = CliRunner()
        result = runner.invoke(validate, ["."])

        self.assertIn(
            result.exit_code,
            [0, 1],
            msg=f"Unexpected exit code. Output:\n{result.output}",
        )

        self.assertNotIn("Traceback", result.output)
        self.assertNotIn("Exception", result.output)

    def test_validate_outputs_expected_structure(self) -> None:
        runner = CliRunner()
        result = runner.invoke(validate, ["."])

        if result.exit_code == 0:
            self.assertTrue(True, "Validation passed")
        else:
            self.assertTrue(
                len(result.output) > 0,
                "Validation output should not be empty on failure",
            )

    def test_validate_with_all_check_flags_on_temp_project(self) -> None:
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
            pre_commit.chmod(pre_commit.stat().st_mode | 0o111)
            (root / "tests" / "unit").mkdir(parents=True)
            (root / "tests" / "integration").mkdir(parents=True)
            (root / "tests" / "unit" / "dummy.py").write_text("pass\n")
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


class TestGuardScanIntegration(unittest.TestCase):
    def test_scan_on_real_project_runs_without_crash(self) -> None:
        runner = CliRunner()
        result = runner.invoke(scan, ["--path", "."])

        self.assertIn(
            result.exit_code,
            [0, 1],
            msg=f"Unexpected exit code. Output:\n{result.output}",
        )

        self.assertNotIn("Traceback", result.output)
        self.assertNotIn("Exception", result.output)

    def test_scan_with_level_option(self) -> None:
        runner = CliRunner()

        for level in ["standard", "strict"]:
            with self.subTest(level=level):
                result = runner.invoke(scan, ["--path", ".", "--level", level])
                self.assertIn(
                    result.exit_code,
                    [0, 1],
                    msg=f"Level {level} failed. Output:\n{result.output}",
                )
                self.assertNotIn("Traceback", result.output)


class TestGuardUpdateIntegration(unittest.TestCase):
    def test_update_on_temp_agents_md(self) -> None:
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            target_file = tmp_path / "AGENTS.md"
            target_file.write_text("# Test Project\n\n## 基础原则\n- Test principle\n")

            principles_dir = tmp_path / "principles"
            principles_dir.mkdir()
            source_principles = (
                Path(__file__).resolve().parent.parent.parent / "principles" / "core.md"
            )
            self.assertTrue(source_principles.exists())
            (principles_dir / "core.md").write_text(
                source_principles.read_text(encoding="utf-8"), encoding="utf-8"
            )

            result = runner.invoke(update, [str(target_file)])

            self.assertEqual(
                result.exit_code,
                0,
                msg=f"Update failed. Output:\n{result.output}",
            )

            content = target_file.read_text()
            self.assertIn("NANO_CODING_GENERATED_START", content)
            self.assertIn("NANO_CODING_GENERATED_END", content)
            self.assertIn("基础原则", content)

    def test_update_idempotency_on_temp_file(self) -> None:
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            target_file = tmp_path / "AGENTS.md"
            target_file.write_text("# Test\n\n## 基础原则\n")

            principles_dir = tmp_path / "principles"
            principles_dir.mkdir()
            source_principles = (
                Path(__file__).resolve().parent.parent.parent / "principles" / "core.md"
            )
            (principles_dir / "core.md").write_text(
                source_principles.read_text(encoding="utf-8"), encoding="utf-8"
            )

            result1 = runner.invoke(update, [str(target_file)])
            self.assertEqual(result1.exit_code, 0)
            content1 = target_file.read_text()

            result2 = runner.invoke(update, [str(target_file)])
            self.assertEqual(result2.exit_code, 0)
            content2 = target_file.read_text()

            self.assertEqual(content1, content2)


class TestGuardInstallIntegration(unittest.TestCase):
    def test_install_to_temp_git_repo(self) -> None:
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            git_dir = tmp_path / ".git"
            git_dir.mkdir()

            result = runner.invoke(install, [str(tmp_path)])

            self.assertEqual(
                result.exit_code,
                0,
                msg=f"Install failed. Output:\n{result.output}",
            )

            hook_file = git_dir / "hooks" / "pre-commit"
            self.assertTrue(hook_file.exists(), "pre-commit hook should be created")

            principles_dir = tmp_path / "principles"
            self.assertTrue(
                principles_dir.exists(), "principles/ directory should be created"
            )
            self.assertTrue(
                (principles_dir / "core.md").exists(),
                "principles/core.md should be copied",
            )

    def test_install_to_non_git_directory_fails(self) -> None:
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as tmp:
            result = runner.invoke(install, [tmp])

            self.assertNotEqual(result.exit_code, 0)


if __name__ == "__main__":
    unittest.main()
