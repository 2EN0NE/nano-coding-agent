"""Integration tests for local agent flow: install -> local skill execution."""

import os
import subprocess
import sys
from pathlib import Path

import nano_coding


PROJECT_ROOT = Path(nano_coding.__file__).resolve().parent.parent


def run_cli(
    cwd: Path, *args: str, extra_env: dict | None = None
) -> subprocess.CompletedProcess:
    env = {**os.environ, "PYTHONPATH": str(PROJECT_ROOT)}
    if extra_env:
        env.update(extra_env)
    return subprocess.run(
        [sys.executable, "-m", "nano_coding.cli", *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        env=env,
    )


def test_install_creates_full_agent_structure(tmp_path: Path) -> None:
    git_dir = tmp_path / ".git"
    git_dir.mkdir()

    result = run_cli(tmp_path, "install", str(tmp_path))
    assert result.returncode == 0, result.stderr

    agent_dir = tmp_path / ".nano-coding-agent"
    assert (agent_dir / "skills").is_dir()
    assert (agent_dir / "hooks").is_dir()
    assert (agent_dir / "principles").is_dir()
    assert (agent_dir / "version").exists()
    assert (agent_dir / "config.yaml").exists()
    assert (agent_dir / "AGENTS.md").exists()
    assert (agent_dir / "principles" / "core.md").exists()
    assert (agent_dir / "hooks" / "pre-commit").exists()

    global_hook = git_dir / "hooks" / "pre-commit"
    assert global_hook.exists()
    assert os.access(global_hook, os.X_OK)


def test_local_skill_registered_and_executable(tmp_path: Path) -> None:
    git_dir = tmp_path / ".git"
    git_dir.mkdir()

    install_result = run_cli(tmp_path, "install", str(tmp_path))
    assert install_result.returncode == 0, install_result.stderr

    skill_dir = tmp_path / ".nano-coding-agent" / "skills" / "hello"
    skill_dir.mkdir(parents=True)

    skill_md = skill_dir / "SKILL.md"
    skill_md.write_text(
        "---\n"
        "name: hello\n"
        "description: A test hello skill\n"
        "type: python\n"
        "entrypoint: main:cli\n"
        "---\n"
        "Hello local skill.\n",
        encoding="utf-8",
    )

    main_py = skill_dir / "main.py"
    main_py.write_text(
        "import click\n\n"
        "def _hello():\n"
        '    click.echo("Hello from local skill!")\n\n'
        'cli = click.Command(name="hello", callback=_hello)\n',
        encoding="utf-8",
    )

    help_result = run_cli(tmp_path, "--help")
    assert help_result.returncode == 0, help_result.stderr
    assert "hello" in help_result.stdout

    exec_result = run_cli(tmp_path, "hello")
    assert exec_result.returncode == 0, exec_result.stderr
    assert "Hello from local skill!" in exec_result.stdout


def test_version_mismatch_warns_but_does_not_abort(tmp_path: Path) -> None:
    git_dir = tmp_path / ".git"
    git_dir.mkdir()

    install_result = run_cli(tmp_path, "install", str(tmp_path))
    assert install_result.returncode == 0, install_result.stderr

    version_file = tmp_path / ".nano-coding-agent" / "version"
    version_file.write_text("999.999.999", encoding="utf-8")

    result = run_cli(tmp_path, "--help")
    assert result.returncode == 0, result.stderr
    assert "WARNING" in result.stderr or "warning" in result.stderr.lower()
    assert "999.999.999" in result.stderr


def test_legacy_project_validate_and_scan(tmp_path: Path) -> None:
    git_dir = tmp_path / ".git"
    git_dir.mkdir()

    (tmp_path / "AGENTS.md").write_text(
        "# Project\n\n## 基础原则\nSome rules.\n",
        encoding="utf-8",
    )
    (tmp_path / "README.md").write_text(
        "# Project\n\nRun tests: `pytest -v`\n",
        encoding="utf-8",
    )
    tests_dir = tmp_path / "tests"
    (tests_dir / "unit").mkdir(parents=True)
    (tests_dir / "integration").mkdir(parents=True)
    (tests_dir / "unit" / "test_dummy.py").write_text("def test_dummy(): pass\n")
    (tests_dir / "integration" / "test_dummy.py").write_text("def test_dummy(): pass\n")

    validate_result = run_cli(tmp_path, "validate", str(tmp_path))
    assert validate_result.returncode in [0, 1], validate_result.stderr
    assert "Traceback" not in validate_result.stderr
    assert "Exception" not in validate_result.stderr

    scan_result = run_cli(tmp_path, "scan", "--path", str(tmp_path))
    assert scan_result.returncode in [0, 1], scan_result.stderr
    assert "Traceback" not in scan_result.stderr
    assert "Exception" not in scan_result.stderr
