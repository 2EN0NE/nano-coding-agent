import os
import subprocess
import tempfile
import unittest
from pathlib import Path


class TestEndToEnd(unittest.TestCase):
    def test_full_guardian_workflow(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            subprocess.run(["git", "init", str(root)], check=True, capture_output=True)

            agents_md = root / "AGENTS.md"
            agents_md.write_text("# Project\n\n## 基础原则\n- TDD first\n")

            src_dir = root / "src"
            src_dir.mkdir()
            (src_dir / "hello.py").write_text('print("hello")\n')

            tests_dir = root / "tests"
            tests_dir.mkdir()
            (tests_dir / "test_dummy.py").write_text(
                "def test_dummy():\n    assert True\n"
            )

            install_result = subprocess.run(
                ["python3", "-m", "guardian.cli", "install", str(root)],
                capture_output=True,
                text=True,
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
            )
            self.assertNotIn("ImportError", hook_result.stderr)
            self.assertNotIn("Traceback", hook_result.stderr)
            self.assertIn(hook_result.returncode, [0, 1])

            validate_result = subprocess.run(
                ["python3", "-m", "guardian.cli", "validate", str(root)],
                capture_output=True,
                text=True,
            )
            self.assertEqual(
                validate_result.returncode,
                0,
                msg=validate_result.stdout + validate_result.stderr,
            )

            principles = (
                Path(__file__).resolve().parent.parent.parent / "principles" / "core.md"
            )
            merge_result = subprocess.run(
                [
                    "python3",
                    "-m",
                    "guardian.cli",
                    "merge",
                    "--principles",
                    str(principles),
                    "--target",
                    str(agents_md),
                ],
                capture_output=True,
                text=True,
            )
            self.assertEqual(merge_result.returncode, 0, msg=merge_result.stderr)

            scan_result = subprocess.run(
                ["python3", "-m", "guardian.cli", "scan", "--path", str(root)],
                capture_output=True,
                text=True,
            )
            self.assertNotIn("Traceback", scan_result.stderr)
