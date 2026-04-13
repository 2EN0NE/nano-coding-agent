import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from nano_coding.cli import cli as root_cli


class TestPrincipleReviewCli(unittest.TestCase):
    def test_help_contains_examples_and_nano_coding(self) -> None:
        runner = CliRunner()
        result = runner.invoke(root_cli, ["principle-review", "--help"])
        self.assertEqual(result.exit_code, 0, msg=result.output)
        self.assertIn("Examples:", result.output)
        self.assertIn("nano-coding", result.output)

    def test_no_flags_runs_all_checks(self) -> None:
        runner = CliRunner()
        with (
            patch(
                "nano_coding.skills.principle_review._run_check_changes"
            ) as mock_changes,
            patch(
                "nano_coding.skills.principle_review._run_separate_concerns"
            ) as mock_separate,
            patch(
                "nano_coding.skills.principle_review._run_length_limit"
            ) as mock_length,
        ):
            mock_changes.return_value = True
            mock_separate.return_value = True
            result = runner.invoke(root_cli, ["principle-review", "."])
            self.assertEqual(result.exit_code, 0, msg=result.output)
            mock_changes.assert_called_once()
            mock_separate.assert_called_once()
            mock_length.assert_called_once()

    def test_check_changes_detects_modified_core_doc(self) -> None:
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            subprocess.run(["git", "init"], cwd=tmpdir, capture_output=True, check=True)
            subprocess.run(
                ["git", "config", "user.email", "test@test.com"],
                cwd=tmpdir,
                capture_output=True,
                check=True,
            )
            subprocess.run(
                ["git", "config", "user.name", "Test"],
                cwd=tmpdir,
                capture_output=True,
                check=True,
            )

            agents_md = tmp_path / "AGENTS.md"
            agents_md.write_text("initial", encoding="utf-8")
            subprocess.run(
                ["git", "add", "AGENTS.md"],
                cwd=tmpdir,
                capture_output=True,
                check=True,
            )
            subprocess.run(
                ["git", "commit", "-m", "init"],
                cwd=tmpdir,
                capture_output=True,
                check=True,
            )

            agents_md.write_text("modified", encoding="utf-8")

            result = runner.invoke(
                root_cli, ["principle-review", "--check-changes", tmpdir]
            )
            self.assertEqual(result.exit_code, 1, msg=result.output)
            self.assertIn("AGENTS.md", result.output)

    def test_check_changes_ok_when_no_changes(self) -> None:
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            subprocess.run(["git", "init"], cwd=tmpdir, capture_output=True, check=True)
            subprocess.run(
                ["git", "config", "user.email", "test@test.com"],
                cwd=tmpdir,
                capture_output=True,
                check=True,
            )
            subprocess.run(
                ["git", "config", "user.name", "Test"],
                cwd=tmpdir,
                capture_output=True,
                check=True,
            )

            agents_md = tmp_path / "AGENTS.md"
            agents_md.write_text("initial", encoding="utf-8")
            subprocess.run(
                ["git", "add", "AGENTS.md"],
                cwd=tmpdir,
                capture_output=True,
                check=True,
            )
            subprocess.run(
                ["git", "commit", "-m", "init"],
                cwd=tmpdir,
                capture_output=True,
                check=True,
            )

            result = runner.invoke(
                root_cli, ["principle-review", "--check-changes", tmpdir]
            )
            self.assertEqual(result.exit_code, 0, msg=result.output)
            self.assertIn("[OK]", result.output)

    def test_check_changes_not_git_repo(self) -> None:
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as tmpdir:
            result = runner.invoke(
                root_cli, ["principle-review", "--check-changes", tmpdir]
            )
            self.assertEqual(result.exit_code, 1, msg=result.output)
            self.assertIn("Not a git repository", result.output)

    def test_separate_concerns_pass(self) -> None:
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as tmpdir:
            agents_md = Path(tmpdir) / "AGENTS.md"
            content = (
                "<!-- NANO_CODING_GENERATED_START -->\n"
                "some content\n"
                "---\n"
                "more content\n"
                "<!-- NANO_CODING_GENERATED_END -->\n"
            )
            agents_md.write_text(content, encoding="utf-8")
            result = runner.invoke(
                root_cli, ["principle-review", "--separate-concerns", tmpdir]
            )
            self.assertEqual(result.exit_code, 0, msg=result.output)
            self.assertIn("[OK]", result.output)

    def test_separate_concerns_fail(self) -> None:
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as tmpdir:
            agents_md = Path(tmpdir) / "AGENTS.md"
            agents_md.write_text("missing markers", encoding="utf-8")
            result = runner.invoke(
                root_cli, ["principle-review", "--separate-concerns", tmpdir]
            )
            self.assertEqual(result.exit_code, 1, msg=result.output)
            self.assertIn("[FAIL]", result.output)

    def test_length_limit_warn(self) -> None:
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as tmpdir:
            agents_md = Path(tmpdir) / "AGENTS.md"
            agents_md.write_text(
                "\n".join([f"line {i}" for i in range(1002)]),
                encoding="utf-8",
            )
            result = runner.invoke(
                root_cli, ["principle-review", "--length-limit", tmpdir]
            )
            self.assertEqual(result.exit_code, 0, msg=result.output)
            self.assertIn("[WARNING]", result.output)

    def test_length_limit_ok(self) -> None:
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            principles_dir = tmp_path / "principles"
            principles_dir.mkdir(parents=True)
            core_md = Path("principles/core.md")
            self.assertTrue(
                core_md.exists(),
                "principles/core.md should exist in the repository",
            )
            (principles_dir / "core.md").write_text(
                core_md.read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            result = runner.invoke(
                root_cli, ["principle-review", "--length-limit", tmpdir]
            )
            self.assertEqual(result.exit_code, 0, msg=result.output)
            self.assertIn("[OK]", result.output)


if __name__ == "__main__":
    unittest.main()
