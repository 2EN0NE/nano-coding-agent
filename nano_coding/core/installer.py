import shutil
import stat
import sys
from pathlib import Path
from typing import Any

import click

from nano_coding import __version__
from nano_coding.agent.skills import BUILTIN_SKILL_NAMES
from nano_coding.core import skill_generator

try:
    from importlib.resources import files  # nosemgrep
except ImportError:

    def files(package: str) -> Any:
        parts = package.split(".")
        mod = __import__(package, fromlist=["__file__"])
        path = Path(mod.__file__).resolve().parent
        for part in parts[1:]:
            path = path / part
        return _PackagePath(path)

    class _PackagePath:
        def __init__(self, path: Path) -> None:
            self._path = path

        def __truediv__(self, other: str) -> "_PackagePath":
            return _PackagePath(self._path / other)

        def read_text(self, encoding: str = "utf-8") -> str:
            return self._path.read_text(encoding=encoding)

        def read_bytes(self) -> bytes:
            return self._path.read_bytes()


def _read_agent_text(relative_path: str) -> str:
    pkg_path = files("nano_coding.agent") / relative_path
    return pkg_path.read_text(encoding="utf-8")


def install_agent(target_dir: str) -> None:
    target = Path(target_dir).resolve()
    git_dir = target / ".git"
    if not git_dir.is_dir():
        click.echo(
            f"[ERROR] {target} is not a git repository (.git directory missing)",
            err=True,
        )
        sys.exit(1)

    agent_dir = target / ".nano-coding-agent"
    agent_dir.mkdir(parents=True, exist_ok=True)
    (agent_dir / "skills").mkdir(parents=True, exist_ok=True)
    (agent_dir / "hooks").mkdir(parents=True, exist_ok=True)
    (agent_dir / "principles").mkdir(parents=True, exist_ok=True)

    version_file = agent_dir / "version"
    version_file.write_text(__version__, encoding="utf-8")

    config_file = agent_dir / "config.json"
    if not config_file.exists():
        config_file.write_text(
            _read_agent_text("templates/config.json.template"), encoding="utf-8"
        )

    agents_md_file = agent_dir / "AGENTS.md"
    if not agents_md_file.exists():
        agents_md_file.write_text(
            _read_agent_text("templates/AGENTS.md.template"), encoding="utf-8"
        )

    source_principles = (
        Path(__file__).resolve().parent.parent.parent / "principles" / "core.md"
    )
    dest_principles = agent_dir / "principles" / "core.md"
    if not dest_principles.exists():
        shutil.copy(str(source_principles), str(dest_principles))

    dest_hook = agent_dir / "hooks" / "pre-commit"
    dest_hook.write_text(
        _read_agent_text("hooks/pre-commit.template"), encoding="utf-8"
    )
    dest_hook.chmod(
        dest_hook.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
    )

    skill_generator.write_skills_to_agent_dir(
        agent_dir, force=False, names=BUILTIN_SKILL_NAMES
    )

    global_hook = git_dir / "hooks" / "pre-commit"
    global_hook.parent.mkdir(parents=True, exist_ok=True)
    global_hook.write_text(
        _read_agent_text("hooks/pre-commit.template"), encoding="utf-8"
    )
    global_hook.chmod(
        global_hook.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
    )

    click.echo(f"Installed nano-coding agent to {agent_dir}")
    click.echo(f"Installed global hook dispatcher to {global_hook}")
