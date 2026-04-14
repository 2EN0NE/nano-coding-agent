"""Local skill loader: discovers and loads skills from .nano-coding-agent/skills/."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

import click

from nano_coding.core.skill_parser import load_skill_from_file

_PYTHON_ENTRY_FILES = ("__init__.py", "main.py", "cli.py")


def _has_python_module(skill_dir: Path) -> bool:
    return any((skill_dir / f).is_file() for f in _PYTHON_ENTRY_FILES)


def discover_local_skills(agent_dir: Path) -> list[dict[str, Any]]:
    """Scan *agent_dir/skills/* and return metadata for each local skill."""
    skills_dir = agent_dir / "skills"
    if not skills_dir.is_dir():
        return []

    skills: list[dict[str, Any]] = []
    for subdir in sorted(skills_dir.iterdir()):
        if not subdir.is_dir():
            continue

        skill_md = subdir / "SKILL.md"
        metadata: dict[str, Any] = {}
        if skill_md.is_file():
            try:
                metadata = load_skill_from_file(skill_md)
            except Exception:
                metadata = {}

        skills.append(
            {
                "name": subdir.name,
                "skill_dir": subdir,
                "metadata": metadata,
                "has_python_module": _has_python_module(subdir),
            }
        )

    return skills


def load_python_skill(skill_dir: Path, entrypoint: str) -> click.Command | None:
    """Dynamically import a Python skill from *skill_dir* via *entrypoint*.

    *entrypoint* format: ``module.path:function_name``.
    """
    if ":" not in entrypoint:
        return None

    module_path, func_name = entrypoint.split(":", 1)
    module_path = module_path.strip()
    func_name = func_name.strip()
    if not module_path or not func_name:
        return None

    # Resolve module path to a file inside skill_dir
    parts = module_path.split(".")
    candidate = skill_dir / Path(*parts).with_suffix(".py")
    if candidate.is_file():
        file_path = candidate
    else:
        candidate = skill_dir / Path(*parts) / "__init__.py"
        if candidate.is_file():
            file_path = candidate
        else:
            return None

    # Ensure we do not leave stray entries in sys.path or sys.modules
    original_sys_path = list(sys.path)
    skill_dir_str = str(skill_dir)
    inserted = False
    if skill_dir_str not in sys.path:
        sys.path.insert(0, skill_dir_str)
        inserted = True

    module_name = (
        f"_nano_coding_local_skill_{skill_dir.name}_{module_path.replace('.', '_')}"
    )
    try:
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        if spec is None or spec.loader is None:
            return None

        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)

        obj = getattr(module, func_name, None)
        if isinstance(obj, click.Command):
            return obj
        return None
    except Exception:
        return None
    finally:
        sys.modules.pop(module_name, None)
        if inserted:
            try:
                sys.path.remove(skill_dir_str)
            except ValueError:
                pass
        # Defensive: restore full list in case something else mutated it
        sys.path[:] = original_sys_path


def resolve_skill(name: str, agent_dir: Path) -> click.Command | None:
    """Look up a local skill by *name* and return its ``click.Command`` if available."""
    skills = discover_local_skills(agent_dir)
    for skill in skills:
        if skill["name"] == name:
            entrypoint = skill["metadata"].get("entrypoint")
            if entrypoint and skill["has_python_module"]:
                return load_python_skill(skill["skill_dir"], entrypoint)
            return None
    return None
