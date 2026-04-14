"""Project discovery utilities for finding agent configuration directories."""

from __future__ import annotations

from pathlib import Path

AGENT_DIR_NAME = ".nano-coding-agent"
GIT_DIR_NAME = ".git"


def find_git_root(start_dir: Path) -> Path | None:
    """Traverse upward from start_dir to find the nearest directory containing .git.

    Args:
        start_dir: The directory to start searching from.

    Returns:
        Path to the directory containing .git, or None if not found.
    """
    current = start_dir.resolve()
    while True:
        if (current / GIT_DIR_NAME).exists():
            return current
        parent = current.parent
        if parent == current:
            break
        current = parent
    return None


def find_project_agent_dirs(start_dir: Path) -> list[Path]:
    """Collect all .nano-coding-agent directories from start_dir up to git root.

    Args:
        start_dir: The directory to start searching from.

    Returns:
        List of Paths to .nano-coding-agent directories, ordered from deepest
        (closest to start_dir) to shallowest (closest to git root).
        Returns an empty list if no git root is found or no agent dirs exist.
    """
    git_root = find_git_root(start_dir)
    if git_root is None:
        return []

    agent_dirs: list[Path] = []
    current = start_dir.resolve()
    while True:
        agent_dir = current / AGENT_DIR_NAME
        if agent_dir.is_dir():
            agent_dirs.append(agent_dir)
        if (current / GIT_DIR_NAME).exists():
            break
        parent = current.parent
        if parent == current:
            break
        current = parent
    return agent_dirs


def find_nearest_agent_dir(start_dir: Path) -> Path | None:
    """Return the nearest (deepest) .nano-coding-agent directory from start_dir.

    Args:
        start_dir: The directory to start searching from.

    Returns:
        Path to the nearest .nano-coding-agent directory, or None if not found
        within the git repository boundary.
    """
    agent_dirs = find_project_agent_dirs(start_dir)
    return agent_dirs[0] if agent_dirs else None
