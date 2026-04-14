import shutil
import stat
import sys
from pathlib import Path

from nano_coding import __version__
from nano_coding.core import skill_generator


DEFAULT_CONFIG = "{}"

DEFAULT_AGENTS_MD = """# Agent Context

This is the project-level agent context for the nano-coding-agent toolchain.
Place project-specific rules, conventions, and principles here.
"""

GLOBAL_HOOK_DISPATCHER = """#!/usr/bin/env bash
set -e
if [ -f ".nano-coding-agent/hooks/pre-commit" ]; then
    bash ".nano-coding-agent/hooks/pre-commit"
else
    python3 -m nano_coding.cli scan --path .
    python3 -m nano_coding.cli validate .
fi
"""


def install_agent(target_dir: str) -> None:
    target = Path(target_dir).resolve()
    git_dir = target / ".git"
    if not git_dir.is_dir():
        print(f"[ERROR] {target} is not a git repository (.git directory missing)")
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
        config_file.write_text(DEFAULT_CONFIG, encoding="utf-8")

    agents_md_file = agent_dir / "AGENTS.md"
    if not agents_md_file.exists():
        agents_md_file.write_text(DEFAULT_AGENTS_MD, encoding="utf-8")

    source_principles = (
        Path(__file__).resolve().parent.parent.parent / "principles" / "core.md"
    )
    dest_principles = agent_dir / "principles" / "core.md"
    if not dest_principles.exists():
        shutil.copy(str(source_principles), str(dest_principles))

    source_hook = Path(__file__).resolve().parent.parent / "hooks" / "pre-commit"
    dest_hook = agent_dir / "hooks" / "pre-commit"
    shutil.copy(str(source_hook), str(dest_hook))

    skill_generator.write_skills_to_agent_dir(agent_dir, force=False)

    global_hook = git_dir / "hooks" / "pre-commit"
    global_hook.parent.mkdir(parents=True, exist_ok=True)
    global_hook.write_text(GLOBAL_HOOK_DISPATCHER, encoding="utf-8")
    global_hook.chmod(
        global_hook.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
    )

    print(f"Installed nano-coding agent to {agent_dir}")
    print(f"Installed global hook dispatcher to {global_hook}")
