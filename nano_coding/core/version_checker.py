from __future__ import annotations

from pathlib import Path

import click

from nano_coding import __version__


def get_global_version() -> str:
    return __version__


def get_local_version(agent_dir: Path) -> str | None:
    version_file = agent_dir / "version"
    if version_file.exists():
        return version_file.read_text().strip()
    return None


def check_version(agent_dir: Path) -> None:
    local = get_local_version(agent_dir)
    if local is None:
        return
    global_ver = get_global_version()
    if local != global_ver:
        click.echo(
            f"\033[33mWARNING: Local agent version ({local}) does not match global version ({global_ver}).\033[0m",
            err=True,
            color=True,
        )
