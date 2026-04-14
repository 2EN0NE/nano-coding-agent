import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class TestEndToEnd(unittest.TestCase):
    def test_full_guardian_workflow(self) -> None:
        project_root = Path(__file__).resolve().parent.parent.parent
        env = {**os.environ, "PYTHONPATH": str(project_root)}

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            subprocess.run(["git", "init", str(root)], check=True, capture_output=True)

            agents_md = root / "AGENTS.md"
            agents_md.write_text("# Project\n\n## 基础原则\n- TDD first\n")

            readme_md = root / "README.md"
            readme_md.write_text(
                "# Project\n\n## Tests\nRun `pytest -v` to execute tests.\n"
            )

            background_md = root / "BACKGROUND.md"
            background_md.write_text(
                "# Background\n\nProject vision and constraints.\n"
            )

            banned_md = root / "BANNED-AGENT-BEHAVIORS.md"
            banned_md.write_text(
                "# Banned Agent Behaviors\n\n## Forbidden Actions\n- Do not hardcode secrets\n"
            )

            src_dir = root / "src"
            src_dir.mkdir()
            (src_dir / "hello.py").write_text(
                'import sys\nsys.stdout.write("hello\\n")\n'
            )

            unit_tests_dir = root / "tests" / "unit"
            integration_tests_dir = root / "tests" / "integration"
            unit_tests_dir.mkdir(parents=True)
            integration_tests_dir.mkdir(parents=True)
            (unit_tests_dir / "test_dummy.py").write_text(
                "def test_dummy():\n    assert True\n"
            )
            (integration_tests_dir / "test_dummy.py").write_text(
                "def test_dummy_integration():\n    assert True\n"
            )

            install_result = subprocess.run(
                ["python3", "-m", "nano_coding.cli", "install", str(root)],
                capture_output=True,
                text=True,
                env=env,
            )
            self.assertEqual(install_result.returncode, 0, msg=install_result.stderr)

            hook = root / ".git" / "hooks" / "pre-commit"
            self.assertTrue(hook.exists())
            self.assertTrue(os.access(hook, os.X_OK))

            hook_result = subprocess.run(
                [str(hook)],
                cwd=str(root),
                capture_output=True,
                text=True,
                env=env,
            )
            self.assertNotIn("ImportError", hook_result.stderr)
            self.assertNotIn("Traceback", hook_result.stderr)
            self.assertIn(hook_result.returncode, [0, 1])

            validate_result = subprocess.run(
                ["python3", "-m", "nano_coding.cli", "validate", str(root)],
                capture_output=True,
                text=True,
                env=env,
            )
            self.assertEqual(
                validate_result.returncode,
                0,
                msg=validate_result.stdout + validate_result.stderr,
            )

            validate_with_checks_result = subprocess.run(
                [
                    "python3",
                    "-m",
                    "nano_coding.cli",
                    "validate",
                    str(root),
                    "--check-agents-abort",
                    "--check-background",
                    "--check-test-separation",
                    "--check-test-commands",
                ],
                capture_output=True,
                text=True,
                env=env,
            )
            self.assertEqual(
                validate_with_checks_result.returncode,
                0,
                msg=validate_with_checks_result.stdout
                + validate_with_checks_result.stderr,
            )

            source_principles = project_root / "principles" / "core.md"
            principles_dir = root / "principles"
            principles_dir.mkdir(exist_ok=True)
            (principles_dir / "core.md").write_text(
                source_principles.read_text(encoding="utf-8"), encoding="utf-8"
            )

            update_result = subprocess.run(
                [
                    "python3",
                    "-m",
                    "nano_coding.cli",
                    "update",
                    str(root),
                ],
                capture_output=True,
                text=True,
                env=env,
            )
            self.assertEqual(update_result.returncode, 0, msg=update_result.stderr)

            scan_result = subprocess.run(
                ["python3", "-m", "nano_coding.cli", "scan", "--path", str(root)],
                capture_output=True,
                text=True,
                env=env,
            )
            self.assertNotIn("Traceback", scan_result.stderr)


class TestPackageInstallationSmoke(unittest.TestCase):
    def test_installed_package_can_run_help(self) -> None:
        project_root = Path(__file__).resolve().parent.parent.parent
        with tempfile.TemporaryDirectory() as tmp:
            venv = Path(tmp) / "venv"
            subprocess.run(
                [sys.executable, "-m", "venv", str(venv)],
                check=True,
                capture_output=True,
            )
            pip = str(venv / "bin" / "pip")
            nano_coding = str(venv / "bin" / "nano-coding")

            subprocess.run(
                [pip, "install", str(project_root)],
                check=True,
                capture_output=True,
            )

            result = subprocess.run(
                [nano_coding, "--help"],
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, msg=result.stderr)
            self.assertIn("nano-coding", result.stdout)


if __name__ == "__main__":
    unittest.main()
