"""SKILL.md generator: creates SKILL.md from click.Command objects."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import click
import yaml

from nano_coding.core.registry import scan_registry


def _find_principles_for_command(command_name: str) -> dict[str, list[str]]:
    """Scan registry to find principles and practices matching the command name."""
    registry = scan_registry()
    matched: dict[str, list[str]] = {}

    for principle, practices in registry.items():
        for practice_name, command_paths_list in practices.items():
            for command_paths in command_paths_list:
                if command_paths and command_paths[0].split()[0] == command_name:
                    if principle not in matched:
                        matched[principle] = []
                    if practice_name not in matched[principle]:
                        matched[principle].append(practice_name)
                    break
    return matched


def generate_skill_md(command: click.Command) -> str:
    """Generate a SKILL.md string for a single click command."""
    if not isinstance(command, click.Command):
        raise TypeError(f"Expected click.Command, got {type(command).__name__}")

    name = command.name or "unknown"
    description = command.get_short_help_str() or ""

    frontmatter: dict[str, Any] = {
        "name": name,
        "description": description,
        "type": "python",
    }

    principles = _find_principles_for_command(name)
    if principles:
        frontmatter["principles"] = principles

    body_lines: list[str] = []

    full_help = command.help or ""
    if full_help:
        body_lines.append(full_help)
        body_lines.append("")

    params: list[str] = []
    for param in command.params:
        if isinstance(param, click.Option):
            opts = "/".join(param.opts)
            param_info = f"- `{opts}`: {param.help or ''}"
            params.append(param_info)
        elif isinstance(param, click.Argument):
            param_info = f"- `<{param.name}>`"
            params.append(param_info)

    if params:
        body_lines.append("## Parameters")
        body_lines.extend(params)
        body_lines.append("")

    body = "\n".join(body_lines).rstrip() + "\n"

    yaml_content = yaml.dump(frontmatter, allow_unicode=True, sort_keys=False)
    return f"---\n{yaml_content}---\n{body}"


def generate_all_skills() -> dict[str, str]:
    """Generate SKILL.md content for all built-in skills."""
    from nano_coding.skills import guard, principle_review

    results: dict[str, str] = {}

    for cmd in guard.commands:
        if isinstance(cmd, click.Command) and cmd.name:
            results[cmd.name] = generate_skill_md(cmd)

    cli = principle_review.cli
    if isinstance(cli, click.Group):
        if cli.commands:
            for sub_name, sub_cmd in cli.commands.items():
                if isinstance(sub_cmd, click.Command) and sub_name:
                    results[sub_name] = generate_skill_md(sub_cmd)
        elif cli.name:
            results[cli.name] = generate_skill_md(cli)
    elif isinstance(cli, click.Command) and cli.name:
        results[cli.name] = generate_skill_md(cli)

    return results


def write_skills_to_agent_dir(
    agent_dir: Path, force: bool = False, names: list[str] | None = None
) -> None:
    """Write generated SKILL.md files to agent_dir/skills/{name}/SKILL.md."""
    agent_dir = Path(agent_dir)
    skills = generate_all_skills()
    if names is not None:
        skills = {name: content for name, content in skills.items() if name in names}

    for name, content in skills.items():
        skill_dir = agent_dir / "skills" / name
        skill_dir.mkdir(parents=True, exist_ok=True)
        skill_file = skill_dir / "SKILL.md"

        if skill_file.exists() and not force:
            continue

        skill_file.write_text(content, encoding="utf-8")
