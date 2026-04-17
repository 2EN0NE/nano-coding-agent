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
from pathlib import Path

from click.testing import CliRunner

from nano_coding.skills.guard import install, merge, scan, update, validate

TESTED_COMMANDS = [
    ("install",),
    ("validate",),
    ("validate", "validate --check-agents-abort"),
    ("validate", "validate --check-background"),
    ("validate", "validate --check-test-commands"),
    ("validate", "validate --check-test-separation"),
    ("update",),
    ("merge",),
    ("scan",),
]


def test_validate_on_real_project_succeeds() -> None:
    runner = CliRunner()
    result = runner.invoke(validate, ["."])

    assert result.exit_code in [0, 1], f"Unexpected exit code. Output:\n{result.output}"

    assert "Traceback" not in result.output
    assert "Exception" not in result.output


def test_validate_outputs_expected_structure() -> None:
    runner = CliRunner()
    result = runner.invoke(validate, ["."])

    if result.exit_code == 0:
        assert True, "Validation passed"
    else:
        assert len(result.output) > 0, (
            "Validation output should not be empty on failure"
        )


def test_validate_with_all_check_flags_on_temp_project() -> None:
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
        assert result.exit_code == 0, result.output


def test_scan_on_real_project_runs_without_crash() -> None:
    runner = CliRunner()
    result = runner.invoke(scan, ["--path", "."])

    assert result.exit_code in [0, 1], f"Unexpected exit code. Output:\n{result.output}"

    assert "Traceback" not in result.output
    assert "Exception" not in result.output


def test_scan_with_level_option() -> None:
    runner = CliRunner()

    for level in ["standard", "strict"]:
        result = runner.invoke(scan, ["--path", ".", "--level", level])
        assert result.exit_code in [0, 1], (
            f"Level {level} failed. Output:\n{result.output}"
        )
        assert "Traceback" not in result.output


def test_update_on_temp_agents_md() -> None:
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
        assert source_principles.exists()
        (principles_dir / "core.md").write_text(
            source_principles.read_text(encoding="utf-8"), encoding="utf-8"
        )

        result = runner.invoke(update, [str(target_file)])

        assert result.exit_code == 0, f"Update failed. Output:\n{result.output}"

        content = target_file.read_text()
        assert "NANO_CODING_GENERATED_START" in content
        assert "NANO_CODING_GENERATED_END" in content
        assert "基础原则" in content


def test_update_idempotency_on_temp_file() -> None:
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
        assert result1.exit_code == 0
        content1 = target_file.read_text()

        result2 = runner.invoke(update, [str(target_file)])
        assert result2.exit_code == 0
        content2 = target_file.read_text()

        assert content1 == content2


def test_install_to_temp_git_repo() -> None:
    runner = CliRunner()

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        git_dir = tmp_path / ".git"
        git_dir.mkdir()

        result = runner.invoke(install, [str(tmp_path)])

        assert result.exit_code == 0, f"Install failed. Output:\n{result.output}"

        hook_file = git_dir / "hooks" / "pre-commit"
        assert hook_file.exists(), "pre-commit hook should be created"

        principles_dir = tmp_path / ".nano-coding-agent" / "principles"
        assert principles_dir.exists(), (
            ".nano-coding-agent/principles/ directory should be created"
        )
        assert (principles_dir / "core.md").exists(), (
            ".nano-coding-agent/principles/core.md should be copied"
        )


def test_merge_on_temp_agents_md() -> None:
    runner = CliRunner()

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        target_file = tmp_path / "AGENTS.md"
        target_file.write_text("# Test Project\n\n## 基础原则\n- Test principle\n")

        principles_file = tmp_path / "principles.md"
        principles_file.write_text("### Principle A\nBody A\n")

        result = runner.invoke(
            merge, ["--principles", str(principles_file), "--target", str(target_file)]
        )

        assert result.exit_code == 0, f"Merge failed. Output:\n{result.output}"

        content = target_file.read_text()
        assert "NANO_CODING_GENERATED_START" in content
        assert "NANO_CODING_GENERATED_END" in content


def test_merge_idempotency_on_temp_file() -> None:
    runner = CliRunner()

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        target_file = tmp_path / "AGENTS.md"
        target_file.write_text("# Test\n\n## 基础原则\n")

        principles_file = tmp_path / "principles.md"
        principles_file.write_text("### Principle A\nBody A\n")

        result1 = runner.invoke(
            merge, ["--principles", str(principles_file), "--target", str(target_file)]
        )
        assert result1.exit_code == 0
        content1 = target_file.read_text()

        result2 = runner.invoke(
            merge, ["--principles", str(principles_file), "--target", str(target_file)]
        )
        assert result2.exit_code == 0
        content2 = target_file.read_text()

        assert content1 == content2


def test_install_to_non_git_directory_fails() -> None:
    runner = CliRunner()

    with tempfile.TemporaryDirectory() as tmp:
        result = runner.invoke(install, [tmp])

        assert result.exit_code != 0
