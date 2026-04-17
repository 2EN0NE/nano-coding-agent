import stat
import subprocess
import tempfile
from pathlib import Path

from click.testing import CliRunner

from nano_coding.skills.guard import scan


def _create_minimal_project(root: Path) -> None:
    (root / "AGENTS.md").write_text("# Project\n\n## 基础原则\nSome rules.\n")
    pre_commit = root / ".git" / "hooks" / "pre-commit"
    pre_commit.parent.mkdir(parents=True)
    pre_commit.write_text("#!/bin/bash\necho hook\n")
    pre_commit.chmod(pre_commit.stat().st_mode | stat.S_IXUSR)
    (root / "tests").mkdir()
    (root / "tests" / "dummy.py").write_text("pass\n")


def test_scan_respects_gitignore() -> None:
    runner = CliRunner()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _create_minimal_project(root)

        subprocess.run(
            ["git", "init"],
            cwd=str(root),
            capture_output=True,
            text=True,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.email", "test@test.com"],
            cwd=str(root),
            capture_output=True,
            text=True,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=str(root),
            capture_output=True,
            text=True,
            check=True,
        )

        (root / ".gitignore").write_text("ignored_dir/\n")

        regular_py = root / "regular.py"
        regular_py.write_text('print("should be scanned")\n')

        ignored_dir = root / "ignored_dir"
        ignored_dir.mkdir()
        ignored_py = ignored_dir / "secret.py"
        ignored_py.write_text('print("should be ignored")\n')

        subprocess.run(
            ["git", "add", "."],
            cwd=str(root),
            capture_output=True,
            text=True,
            check=True,
        )

        result = runner.invoke(scan, ["--path", str(root)])
        assert result.exit_code in [0, 1], (
            f"Unexpected exit code. Output:\n{result.output}"
        )
        assert "Traceback" not in result.output

        assert "regular.py" in result.output, (
            f"Expected regular.py to appear in scan output:\n{result.output}"
        )

        assert "ignored_dir/secret.py" not in result.output, (
            f"Expected ignored_dir/secret.py to be excluded from scan output:\n{result.output}"
        )
        assert "secret.py" not in result.output, (
            f"Expected secret.py to be excluded from scan output:\n{result.output}"
        )
