"""
Integration tests for VibeCoding template generation.

These tests verify that the Copier template generates the expected directory structure
with only the required files (no extra directories).

Run with: pytest tests/integration/test_template_generation.py -v
"""

import os
import subprocess
import tempfile
import shutil
from pathlib import Path
from typing import Set

import pytest


TEMPLATE_DIR = Path(__file__).parent.parent.parent


EXPECTED_ROOT_ITEMS: Set[str] = {
    ".husky",
    ".vibe-coding-workflow",
    "AGENTS.md",
    "BACKGROUND.md",
    "SKILLS.md",
    "BANNED-AGENT-BEHAVIORS.md",
    "docker-compose.yml",
    "Dockerfile.sandbox",
    ".env.docker.example",
}


FORBIDDEN_ROOT_ITEMS: Set[str] = {
    "docs",
    "scripts",
    "knowledge",
    ".beads",
    "tests",
    "AGENTS.md.tmpl",
    "LICENSE",
    "README.md",
    "copier.yml",
}


@pytest.fixture
def generated_project(tmp_path):
    """Generate a temporary project using copier and clean up after test."""
    project_dir = tmp_path / "test_project"
    
    result = subprocess.run(
        [
            "copier", "copy",
            str(TEMPLATE_DIR),
            str(project_dir),
            "-f", "--trust"
        ],
        capture_output=True,
        text=True,
    )
    
    if result.returncode != 0:
        print(f"Copier stderr: {result.stderr}")
        print(f"Copier stdout: {result.stdout}")
    
    yield project_dir
    
    if project_dir.exists():
        shutil.rmtree(project_dir)


def get_root_items(project_path: Path) -> Set[str]:
    """Get all root-level files and directories in a project."""
    root_items = set()
    for item in project_path.iterdir():
        name = item.name
        if name.startswith(".") and name not in EXPECTED_ROOT_ITEMS:
            continue
        root_items.add(name)
    return root_items


def test_generated_project_has_required_files(generated_project):
    """Test that generated project contains all required root-level files."""
    root_items = get_root_items(generated_project)
    
    missing_items = EXPECTED_ROOT_ITEMS - root_items
    assert not missing_items, (
        f"Generated project is missing required items: {missing_items}. "
        f"Found items: {root_items}"
    )


def test_generated_project_has_no_extra_directories(generated_project):
    """Test that generated project does NOT contain forbidden directories."""
    root_items = get_root_items(generated_project)
    
    extra_items = FORBIDDEN_ROOT_ITEMS & root_items
    assert not extra_items, (
        f"Generated project contains forbidden items: {extra_items}. "
        f"These should not appear in generated projects. "
        f"Found items: {root_items}"
    )


def test_vibe_coding_workflow_structure(generated_project):
    """Test that .vibe-coding-workflow/ has the correct subdirectory structure."""
    workflow_dir = generated_project / ".vibe-coding-workflow"
    
    required_subdirs = {"agents", "hooks", "scripts"}
    existing_subdirs = {d.name for d in workflow_dir.iterdir() if d.is_dir()}
    
    missing_subdirs = required_subdirs - existing_subdirs
    assert not missing_subdirs, (
        f".vibe-coding-workflow/ is missing required subdirectories: {missing_subdirs}"
    )
    
    required_files = {"workflow.yaml"}
    existing_files = {f.name for f in workflow_dir.iterdir() if f.is_file()}
    
    missing_files = required_files - existing_files
    assert not missing_files, (
        f".vibe-coding-workflow/ is missing required files: {missing_files}"
    )


def test_husky_hooks_exist(generated_project):
    """Test that .husky/ contains required hook files."""
    husky_dir = generated_project / ".husky"
    
    required_hooks = {"pre-commit", "post-commit"}
    existing_hooks = {f.name for f in husky_dir.iterdir() if f.is_file()}
    
    missing_hooks = required_hooks - existing_hooks
    assert not missing_hooks, (
        f".husky/ is missing required hooks: {missing_hooks}"
    )


def test_no_agents_directory_at_root(generated_project):
    """Test that .agents/ does NOT exist at root level."""
    assert not (generated_project / ".agents").exists(), (
        "Found .agents/ at root level."
    )


def test_no_scripts_directory_at_root(generated_project):
    """Test that scripts/ does NOT exist at root level."""
    assert not (generated_project / "scripts").exists(), (
        "Found scripts/ at root level."
    )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
