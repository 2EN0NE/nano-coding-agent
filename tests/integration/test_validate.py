"""Integration tests for validate command with new suggest checks."""

import stat
import tempfile
from pathlib import Path

from click.testing import CliRunner

from nano_coding.skills.guard import validate

TESTED_COMMANDS = [
    ("validate",),
    ("validate", "validate --check-subdir-agents"),
    ("validate", "validate --check-index-summary"),
    ("validate", "validate --check-knowledge-dir"),
    ("validate", "validate --check-subdir-agents-overflow"),
    ("validate", "validate --check-agents-language"),
    ("validate", "validate --check-readme-i18n"),
    ("validate", "validate --check-background-content"),
    ("validate", "validate --check-gitignore-tempfiles"),
    ("validate", "validate --check-commit-size"),
    ("validate", "validate --check-package-manager"),
    ("validate", "validate --check-agents-length"),
]


def _create_clean_project(root: Path) -> None:
    (root / "AGENTS.md").write_text("# Project\n\n## 基础原则\nSome rules.\n")
    pre_commit = root / ".git" / "hooks" / "pre-commit"
    pre_commit.parent.mkdir(parents=True)
    pre_commit.write_text("#!/bin/bash\necho hook\n")
    pre_commit.chmod(pre_commit.stat().st_mode | stat.S_IXUSR)
    (root / "tests").mkdir()
    (root / "tests" / "dummy.py").write_text("pass\n")


def test_validate_default_runs_all_on_clean_project() -> None:
    runner = CliRunner()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "AGENTS.md").write_text(
            "# Project\n\n## 基础原则\nSome rules.\n\nRun tests: `pytest -v`\n"
        )
        pre_commit = root / ".git" / "hooks" / "pre-commit"
        pre_commit.parent.mkdir(parents=True)
        pre_commit.write_text("#!/bin/bash\necho hook\n")
        pre_commit.chmod(pre_commit.stat().st_mode | stat.S_IXUSR)
        (root / "BANNED-AGENT-BEHAVIORS.md").write_text("# Banned\nDon't do X.\n")
        (root / "BACKGROUND.md").write_text(
            "# Background\n\n愿景、约束、业务逻辑、避坑指南。\n"
        )
        (root / "README.md").write_text(
            "# Project\n\n[中文](./README.zh.md)\n\nRun tests: `pytest -v`\n"
        )
        (root / "README.zh.md").write_text("# 项目\n")
        (root / ".INDEX.md").write_text("# Index\n")
        (root / "knowledge").mkdir()
        (root / "tests" / "unit").mkdir(parents=True)
        (root / "tests" / "integration").mkdir()
        (root / "tests" / "unit" / "dummy.py").write_text("pass\n")
        (root / "tests" / "integration" / "dummy.py").write_text("pass\n")
        subdir = root / "subdir"
        subdir.mkdir()
        (subdir / "AGENTS.md").write_text("# Subdir\n")
        result = runner.invoke(validate, [str(root)])
        assert result.exit_code == 0, result.output
        assert "PASS" in result.output


def test_validate_check_subdir_agents_pass() -> None:
    runner = CliRunner()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _create_clean_project(root)
        result = runner.invoke(validate, [str(root), "--check-subdir-agents"])
        assert result.exit_code == 0, result.output


def test_validate_check_subdir_agents_fail() -> None:
    runner = CliRunner()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _create_clean_project(root)
        for i in range(51):
            (root / f"src{i}.py").write_text("pass\n")
        result = runner.invoke(validate, [str(root), "--check-subdir-agents"])
        assert result.exit_code == 0, result.output
        assert "no sub-directory AGENTS.md found" in result.output


def test_validate_check_index_summary_pass() -> None:
    runner = CliRunner()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _create_clean_project(root)
        (root / ".INDEX.md").write_text("# Index\n")
        result = runner.invoke(validate, [str(root), "--check-index-summary"])
        assert result.exit_code == 0, result.output


def test_validate_check_index_summary_fail() -> None:
    runner = CliRunner()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _create_clean_project(root)
        result = runner.invoke(validate, [str(root), "--check-index-summary"])
        assert result.exit_code == 0, result.output
        assert ".INDEX.md nor .SUMMARY.md" in result.output


def test_validate_check_knowledge_dir_pass() -> None:
    runner = CliRunner()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _create_clean_project(root)
        (root / "knowledge").mkdir()
        result = runner.invoke(validate, [str(root), "--check-knowledge-dir"])
        assert result.exit_code == 0, result.output


def test_validate_check_knowledge_dir_fail() -> None:
    runner = CliRunner()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _create_clean_project(root)
        result = runner.invoke(validate, [str(root), "--check-knowledge-dir"])
        assert result.exit_code == 0, result.output
        assert "knowledge/ directory not found" in result.output


def test_validate_check_agents_language_pass() -> None:
    runner = CliRunner()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _create_clean_project(root)
        result = runner.invoke(validate, [str(root), "--check-agents-language"])
        assert result.exit_code == 0, result.output


def test_validate_check_agents_language_fail() -> None:
    runner = CliRunner()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _create_clean_project(root)
        lines = [f"这是中文 line {i} and english" for i in range(20)]
        (root / "AGENTS.md").write_text(
            "# Project\n\n## 基础原则\n" + "\n".join(lines) + "\n"
        )
        result = runner.invoke(validate, [str(root), "--check-agents-language"])
        assert result.exit_code == 0, result.output
        assert "mixed scripts" in result.output


def test_validate_check_readme_i18n_pass() -> None:
    runner = CliRunner()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _create_clean_project(root)
        (root / "README.md").write_text("# Project\n\n[中文](./README.zh.md)\n")
        (root / "README.zh.md").write_text("# 项目\n")
        result = runner.invoke(validate, [str(root), "--check-readme-i18n"])
        assert result.exit_code == 0, result.output


def test_validate_check_readme_i18n_fail() -> None:
    runner = CliRunner()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _create_clean_project(root)
        (root / "README.md").write_text("# Project\n")
        result = runner.invoke(validate, [str(root), "--check-readme-i18n"])
        assert result.exit_code == 0, result.output
        assert "no translated variants" in result.output


def test_validate_check_background_content_pass() -> None:
    runner = CliRunner()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _create_clean_project(root)
        (root / "BACKGROUND.md").write_text(
            "# Background\n\n愿景、约束、业务逻辑、避坑指南。\n"
        )
        result = runner.invoke(validate, [str(root), "--check-background-content"])
        assert result.exit_code == 0, result.output


def test_validate_check_background_content_fail() -> None:
    runner = CliRunner()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _create_clean_project(root)
        (root / "BACKGROUND.md").write_text("# Background\n\nHello.\n")
        result = runner.invoke(validate, [str(root), "--check-background-content"])
        assert result.exit_code == 0, result.output
        assert "missing recommended keywords" in result.output


def test_validate_check_package_manager_pass() -> None:
    runner = CliRunner()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _create_clean_project(root)
        (root / "package-lock.json").write_text("{}\n")
        (root / "README.md").write_text("Install with `npm install`\n")
        result = runner.invoke(validate, [str(root), "--check-package-manager"])
        assert result.exit_code == 0, result.output


def test_validate_check_package_manager_fail() -> None:
    runner = CliRunner()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _create_clean_project(root)
        (root / "package-lock.json").write_text("{}\n")
        (root / "README.md").write_text("Install with `pnpm install`\n")
        result = runner.invoke(validate, [str(root), "--check-package-manager"])
        assert result.exit_code == 0, result.output
        assert "inconsistent install command" in result.output


def test_validate_check_agents_length_pass() -> None:
    runner = CliRunner()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _create_clean_project(root)
        result = runner.invoke(validate, [str(root), "--check-agents-length"])
        assert result.exit_code == 0, result.output


def test_validate_check_agents_length_fail() -> None:
    runner = CliRunner()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _create_clean_project(root)
        long_line = "- " + "x" * 160
        (root / "AGENTS.md").write_text(f"# Project\n\n### 基础原则\n{long_line}\n")
        result = runner.invoke(validate, [str(root), "--check-agents-length"])
        assert result.exit_code == 0, result.output
        assert "exceeds 150 chars" in result.output


def test_validate_demo_project_with_multiple_violations() -> None:
    """Run validate on a sandbox demo project containing multiple suggest violations."""
    runner = CliRunner()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)

        # --- Base valid structure to avoid old blocking failures ---
        (root / "AGENTS.md").write_text(
            "# Project\n\n## 基础原则\nSome rules.\n\nRun tests: `pytest -v`\n"
        )
        pre_commit = root / ".git" / "hooks" / "pre-commit"
        pre_commit.parent.mkdir(parents=True)
        pre_commit.write_text("#!/bin/bash\necho hook\n")
        pre_commit.chmod(pre_commit.stat().st_mode | stat.S_IXUSR)
        (root / "BANNED-AGENT-BEHAVIORS.md").write_text("# Banned\nDon't do X.\n")
        (root / "tests" / "unit").mkdir(parents=True)
        (root / "tests" / "integration").mkdir()
        (root / "tests" / "unit" / "dummy.py").write_text("pass\n")
        (root / "tests" / "integration" / "dummy.py").write_text("pass\n")

        # --- Violation 1: BACKGROUND.md missing keywords ---
        (root / "BACKGROUND.md").write_text("# Background\n\nHello.\n")

        # --- Violation 2: README.md without i18n variants ---
        (root / "README.md").write_text("# Project\n\nNo language links.\n")

        # --- Violation 3: AGENTS.md practice bullet >150 chars ---
        long_line = "- " + "x" * 160
        (root / "AGENTS.md").write_text(
            "# Project\n\n### 基础原则\nSome rules.\n\nRun tests: `pytest -v`\n"
            + long_line
            + "\n"
        )

        # --- Violation 4: No knowledge/ dir ---
        pass

        # --- Violation 5: No .INDEX.md or .SUMMARY.md ---
        pass

        # --- Violation 6: Large source tree without subdir AGENTS.md ---
        for i in range(51):
            (root / f"src{i}.py").write_text("pass\n")

        # --- Violation 7: Untracked temp file ---
        import subprocess as _sp

        _sp.run(["git", "init"], cwd=str(root), capture_output=True, check=True)
        gitignore = root / ".gitignore"
        gitignore.write_text("*.pyc\n")
        env_file = root / ".env"
        env_file.write_text("SECRET=123\n")

        # --- Violation 8: Package manager mismatch ---
        (root / "package-lock.json").write_text("{}\n")
        (root / "README.md").write_text("# Project\n\nInstall with `pnpm install`\n")

        # --- Violation 9: AGENTS.md mixed scripts ---
        mixed_lines = [f"这是中文 line {i} and english" for i in range(20)]
        current_agents = (root / "AGENTS.md").read_text()
        (root / "AGENTS.md").write_text(current_agents + "\n".join(mixed_lines) + "\n")

        result = runner.invoke(validate, [str(root)])

        # Should be 0 because all new suggest checks are warnings
        assert result.exit_code == 0, result.output

        output = result.output
        assert "missing recommended keywords" in output
        assert "no translated variants" in output
        assert "exceeds 150 chars" in output
        assert "knowledge/ directory not found" in output
        assert ".INDEX.md nor .SUMMARY.md" in output
        assert "no sub-directory AGENTS.md found" in output
        assert ".env" in output
        assert "inconsistent install command" in output
        assert "mixed scripts" in output


def test_validate_long_markdown_document_blocks() -> None:
    """A markdown document exceeding 1000 lines should be blocking."""
    runner = CliRunner()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "AGENTS.md").write_text(
            "# Project\n\n## 基础原则\nSome rules.\n\nRun tests: `pytest -v`\n"
        )
        pre_commit = root / ".git" / "hooks" / "pre-commit"
        pre_commit.parent.mkdir(parents=True)
        pre_commit.write_text("#!/bin/bash\necho hook\n")
        pre_commit.chmod(pre_commit.stat().st_mode | stat.S_IXUSR)
        (root / "tests").mkdir()
        (root / "tests" / "dummy.py").write_text("pass\n")
        (root / "huge_doc.md").write_text("\n".join([f"line {i}" for i in range(1001)]))
        result = runner.invoke(validate, [str(root)])
        assert result.exit_code == 1, result.output
        assert "Document exceeds 1000 lines" in result.output
