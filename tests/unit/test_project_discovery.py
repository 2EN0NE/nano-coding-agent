"""Unit tests for nano_coding.core.project_discovery."""

from pathlib import Path

from nano_coding.core.project_discovery import (
    find_git_root,
    find_nearest_agent_dir,
    find_project_agent_dirs,
)


def test_find_git_root_finds_git(tmp_path: Path) -> None:
    """Should return the directory containing .git."""
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    subdir = tmp_path / "a" / "b"
    subdir.mkdir(parents=True)
    assert find_git_root(subdir) == tmp_path


def test_find_git_root_returns_none_when_no_git(tmp_path: Path) -> None:
    """Should return None when .git is not found anywhere upward."""
    subdir = tmp_path / "nested" / "dir"
    subdir.mkdir(parents=True)
    assert find_git_root(subdir) is None


def test_find_git_root_stops_at_first_git(tmp_path: Path) -> None:
    """Should return the nearest (deepest) git root."""
    outer_git = tmp_path / ".git"
    outer_git.mkdir()
    inner_project = tmp_path / "packages" / "app"
    inner_project.mkdir(parents=True)
    inner_git = inner_project / ".git"
    inner_git.mkdir()
    subdir = inner_project / "src"
    subdir.mkdir()
    assert find_git_root(subdir) == inner_project


def test_find_project_agent_dirs_collects_all_up_to_git_root(tmp_path: Path) -> None:
    """Should collect agent dirs from start_dir up to git root."""
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    agent_root = tmp_path / ".nano-coding-agent"
    agent_root.mkdir()
    pkg = tmp_path / "packages" / "app"
    pkg.mkdir(parents=True)
    agent_pkg = pkg / ".nano-coding-agent"
    agent_pkg.mkdir()
    src = pkg / "src"
    src.mkdir()

    dirs = find_project_agent_dirs(src)
    assert dirs == [agent_pkg, agent_root]


def test_find_project_agent_dirs_returns_empty_when_no_git(tmp_path: Path) -> None:
    """Should return empty list when no git root is found."""
    agent_dir = tmp_path / ".nano-coding-agent"
    agent_dir.mkdir()
    subdir = tmp_path / "src"
    subdir.mkdir()
    assert find_project_agent_dirs(subdir) == []


def test_find_project_agent_dirs_returns_empty_when_no_agents(tmp_path: Path) -> None:
    """Should return empty list when git exists but no agent dirs."""
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    subdir = tmp_path / "src"
    subdir.mkdir()
    assert find_project_agent_dirs(subdir) == []


def test_find_project_agent_dirs_includes_git_root_itself(tmp_path: Path) -> None:
    """Should include agent dir placed at the git root itself."""
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    agent_root = tmp_path / ".nano-coding-agent"
    agent_root.mkdir()
    subdir = tmp_path / "src"
    subdir.mkdir()
    dirs = find_project_agent_dirs(subdir)
    assert dirs == [agent_root]


def test_find_project_agent_dirs_start_dir_is_git_root(tmp_path: Path) -> None:
    """Should work when start_dir is the git root itself."""
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    agent_root = tmp_path / ".nano-coding-agent"
    agent_root.mkdir()
    dirs = find_project_agent_dirs(tmp_path)
    assert dirs == [agent_root]


def test_find_project_agent_dirs_nested_git_priority(tmp_path: Path) -> None:
    """Should stop at the nearest git root, not traverse further."""
    outer_git = tmp_path / ".git"
    outer_git.mkdir()
    outer_agent = tmp_path / ".nano-coding-agent"
    outer_agent.mkdir()

    inner_project = tmp_path / "packages" / "app"
    inner_project.mkdir(parents=True)
    inner_git = inner_project / ".git"
    inner_git.mkdir()
    inner_agent = inner_project / ".nano-coding-agent"
    inner_agent.mkdir()

    src = inner_project / "src"
    src.mkdir()
    dirs = find_project_agent_dirs(src)
    assert dirs == [inner_agent]


def test_find_nearest_agent_dir_returns_deepest(tmp_path: Path) -> None:
    """Should return the nearest (deepest) agent dir."""
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    agent_root = tmp_path / ".nano-coding-agent"
    agent_root.mkdir()
    pkg = tmp_path / "packages" / "app"
    pkg.mkdir(parents=True)
    agent_pkg = pkg / ".nano-coding-agent"
    agent_pkg.mkdir()
    src = pkg / "src"
    src.mkdir()

    nearest = find_nearest_agent_dir(src)
    assert nearest == agent_pkg


def test_find_nearest_agent_dir_returns_none_when_no_git(tmp_path: Path) -> None:
    """Should return None when no git root exists."""
    subdir = tmp_path / "src"
    subdir.mkdir()
    assert find_nearest_agent_dir(subdir) is None


def test_find_nearest_agent_dir_returns_none_when_no_agents(tmp_path: Path) -> None:
    """Should return None when git exists but no agent dirs."""
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    subdir = tmp_path / "src"
    subdir.mkdir()
    assert find_nearest_agent_dir(subdir) is None


def test_find_nearest_agent_dir_single_agent_at_root(tmp_path: Path) -> None:
    """Should return the single agent dir at git root."""
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    agent_root = tmp_path / ".nano-coding-agent"
    agent_root.mkdir()
    subdir = tmp_path / "src"
    subdir.mkdir()
    assert find_nearest_agent_dir(subdir) == agent_root
