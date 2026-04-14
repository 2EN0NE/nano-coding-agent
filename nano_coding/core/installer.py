from __future__ import annotations

import shutil
import stat
import sys
from pathlib import Path
from typing import Any

import click

from nano_coding import __version__
from nano_coding.agent.skills import BUILTIN_SKILL_NAMES
from nano_coding.core import skill_generator
from nano_coding.core.optional_skills import EXTERNAL_TOOLS, INSTALLABLE_SKILLS

try:
    import questionary
except Exception:  # pragma: no cover
    questionary = None  # type: ignore[assignment]

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


def _read_agent_path(relative_path: str) -> Path:
    pkg_path = files("nano_coding.agent") / relative_path
    if hasattr(pkg_path, "_path"):
        return Path(str(pkg_path._path))
    return Path(str(pkg_path))


def _detect_available_clis() -> dict[str, bool]:
    clis: dict[str, bool] = {}
    for tool in EXTERNAL_TOOLS:
        clis[tool["name"]] = shutil.which(tool["name"]) is not None
    for skill in INSTALLABLE_SKILLS:
        for cli in skill.get("requires_cli", []):
            if cli not in clis:
                clis[cli] = shutil.which(cli) is not None
    return clis


def _filter_available_skills(clis: dict[str, bool]) -> list[dict[str, Any]]:
    available: list[dict[str, Any]] = []
    for skill in INSTALLABLE_SKILLS:
        reqs = skill.get("requires_cli", [])
        if all(clis.get(r, False) for r in reqs):
            available.append(skill)
    return available


def _clean_existing_installation(target: Path) -> None:
    agent_dir = target / ".nano-coding-agent"
    if agent_dir.exists():
        shutil.rmtree(agent_dir)
    git_hook = target / ".git" / "hooks" / "pre-commit"
    if git_hook.exists():
        git_hook.unlink()
    opencode_dir = target / ".opencode"
    if opencode_dir.exists():
        agent_file = opencode_dir / "agents" / "nano-coding-agent.md"
        if agent_file.exists():
            agent_file.unlink()
        skills_dir = opencode_dir / "skills"
        if skills_dir.exists():
            for skill in INSTALLABLE_SKILLS:
                skill_dir = skills_dir / skill["name"]
                if skill_dir.exists():
                    shutil.rmtree(skill_dir)


def _prompt_external_tools(clis: dict[str, bool]) -> list[str]:
    available = [t for t in EXTERNAL_TOOLS if clis.get(t["name"], False)]
    if not available:
        return []
    if questionary is None or not sys.stdin.isatty():
        return []
    choices = [
        questionary.Choice(
            title=f"{t['description']} (detected)", value=t["name"], checked=True
        )
        for t in available
    ]
    result = questionary.checkbox(
        "选择要注册到的外部工具（按空格选择，回车确认）：",
        choices=choices,
    ).ask()
    return result if result is not None else []


def _prompt_skills(skills: list[dict[str, Any]]) -> list[str]:
    defaults = [s["name"] for s in skills if s.get("checked", False)]
    if questionary is None or not sys.stdin.isatty():
        return defaults
    choices = [
        questionary.Choice(
            title=f"{s['name']} - {s['description']}",
            value=s["name"],
            checked=s.get("checked", False),
        )
        for s in skills
    ]
    result = questionary.checkbox(
        "选择要安装的 skills（按空格选择，回车确认）：",
        choices=choices,
    ).ask()
    return result if result is not None else defaults


def _prompt_hooks(selected_skills: list[str]) -> list[str]:
    hookable: list[str] = []
    for name in selected_skills:
        for skill in INSTALLABLE_SKILLS:
            if skill["name"] == name and skill.get("hooks"):
                hookable.append(name)
                break
    if not hookable:
        return []
    if questionary is None or not sys.stdin.isatty():
        return hookable
    choices = [
        questionary.Choice(title=f"pre-commit - {name}", value=name, checked=True)
        for name in hookable
    ]
    result = questionary.checkbox(
        "选择要安装的 hooks（按空格选择，回车确认）：",
        choices=choices,
    ).ask()
    return result if result is not None else hookable


def _get_skill_content(name: str, template_dir: str | None) -> str | None:
    if template_dir is not None:
        src = _read_agent_path(template_dir) / "SKILL.md"
        if src.exists():
            return src.read_text(encoding="utf-8")
        return None
    all_skills = skill_generator.generate_all_skills()
    return all_skills.get(name)


def _write_skill_to_dir(base_dir: Path, name: str, content: str) -> None:
    skill_dir = base_dir / "skills" / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    skill_file = skill_dir / "SKILL.md"
    skill_file.write_text(content, encoding="utf-8")


def _install_skills_to_agent_dir(agent_dir: Path, selected_skills: list[str]) -> None:
    for name in selected_skills:
        template_dir = None
        for skill in INSTALLABLE_SKILLS:
            if skill["name"] == name:
                template_dir = skill.get("template_dir")
                break
        content = _get_skill_content(name, template_dir)
        if content is not None:
            _write_skill_to_dir(agent_dir, name, content)


def _install_hooks(
    target: Path, agent_dir: Path, selected_hook_skills: list[str]
) -> None:
    if not selected_hook_skills:
        return
    git_dir = target / ".git"
    lines = ["#!/usr/bin/env bash", "set -e"]
    for name in selected_hook_skills:
        cmd = None
        for skill in INSTALLABLE_SKILLS:
            if skill["name"] == name:
                cmd = skill.get("hook_cmd")
                break
        if cmd:
            lines.append(cmd)
    content = "\n".join(lines) + "\n"

    dest_hook = agent_dir / "hooks" / "pre-commit"
    dest_hook.write_text(content, encoding="utf-8")
    dest_hook.chmod(
        dest_hook.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
    )

    global_hook = git_dir / "hooks" / "pre-commit"
    global_hook.parent.mkdir(parents=True, exist_ok=True)
    global_hook.write_text(content, encoding="utf-8")
    global_hook.chmod(
        global_hook.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
    )


def _register_to_opencode(target_dir: Path, selected_skills: list[str]) -> None:
    agents_dir = target_dir / ".opencode" / "agents"
    agents_dir.mkdir(parents=True, exist_ok=True)
    agent_file = agents_dir / "nano-coding-agent.md"
    content = (
        "---\n"
        "description: AI coding governance agent for this project\n"
        "mode: primary\n"
        'prompt: "{file:../.nano-coding-agent/AGENTS.md}"\n'
        "---\n"
    )
    agent_file.write_text(content, encoding="utf-8")
    click.echo(f"[INFO] Registered nano-coding-agent as primary agent in {agent_file}")

    opencode_base_dir = target_dir / ".opencode"
    for name in selected_skills:
        template_dir = None
        for skill in INSTALLABLE_SKILLS:
            if skill["name"] == name:
                template_dir = skill.get("template_dir")
                break
        skill_content = _get_skill_content(name, template_dir)
        if skill_content is not None:
            _write_skill_to_dir(opencode_base_dir, name, skill_content)
            click.echo(f"[INFO] Registered skill '{name}' to opencode")


def _register_to_external_tools(
    target_dir: Path, tools: list[str], selected_skills: list[str]
) -> None:
    for tool in tools:
        if tool == "opencode":
            _register_to_opencode(target_dir, selected_skills)
        else:
            click.echo(f"[INFO] Registered agent to {tool} (placeholder)")


def install_agent(target_dir: str, interactive: bool = False) -> None:
    target = Path(target_dir).resolve()
    git_dir = target / ".git"
    if not git_dir.is_dir():
        click.echo(
            f"[ERROR] {target} is not a git repository (.git directory missing)",
            err=True,
        )
        sys.exit(1)

    _clean_existing_installation(target)

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

    selected_tools: list[str] = []
    selected_skills: list[str] = BUILTIN_SKILL_NAMES
    selected_hooks: list[str] = ["validate", "scan"]
    if interactive:
        clis = _detect_available_clis()
        available_skills = _filter_available_skills(clis)
        selected_tools = _prompt_external_tools(clis)
        selected_skills = _prompt_skills(available_skills)
        selected_hooks = _prompt_hooks(selected_skills)
        _install_skills_to_agent_dir(agent_dir, selected_skills)
        _install_hooks(target, agent_dir, selected_hooks)
        if selected_tools:
            _register_to_external_tools(target, selected_tools, selected_skills)
    else:
        _install_skills_to_agent_dir(agent_dir, selected_skills)
        _install_hooks(target, agent_dir, selected_hooks)

    click.echo(f"Installed nano-coding agent to {agent_dir}")
    if selected_hooks:
        click.echo(f"Installed hooks: pre-commit ({', '.join(selected_hooks)})")
    if selected_skills:
        click.echo(f"Installed skills: {', '.join(selected_skills)}")
    if selected_tools:
        click.echo(f"Registered to external tools: {', '.join(selected_tools)}")
