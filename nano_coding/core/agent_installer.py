import os
import shutil
import stat
import subprocess
from pathlib import Path

import click

DEFAULT_AGENT_YAML = """\
agent_id: nano-coding-agent
version: "0.1.0"
model:
  provider: anthropic
  id: claude-sonnet-4-6
  contextWindow: 200000
  maxTokens: 8192
api_key_source: env:KIMI_API_KEY
skills:
  - governance
  - knowledge
"""

CURSOR_RULES = """# nano-coding-agent

This project has a local nano-coding-agent installed in `.nano-coding-agent/`.
For governance checks, pre-commit review, and project knowledge queries, delegate to the agent:

- Run checks: `node .nano-coding-agent/ai-core/dist/index.js run "review staged changes"`
- Learn: `node .nano-coding-agent/ai-core/dist/index.js learn "..."`
- Ask: `node .nano-coding-agent/ai-core/dist/index.js ask "..."`

Always read `.nano-coding-agent/knowledge/` before making architectural decisions.
"""

CLAUDE_REGISTRATION = """# nano-coding-agent

This project has a local nano-coding-agent installed in `.nano-coding-agent/`.
The agent runs on the pi.dev kernel and maintains project knowledge.

When you need to run governance checks or record project decisions, invoke:
- `node .nano-coding-agent/ai-core/dist/index.js run "prompt"`
- `node .nano-coding-agent/ai-core/dist/index.js learn "content"`

Read `.nano-coding-agent/knowledge/decisions/` and `.nano-coding-agent/knowledge/patterns/`
for accumulated project wisdom.
"""

OPENCODE_REGISTRATION = """# nano-coding-agent Skill

This project has a local nano-coding-agent installed in `.nano-coding-agent/`.
The agent runs on the pi.dev kernel and maintains project knowledge.

Invoke the agent via:
- `node .nano-coding-agent/ai-core/dist/index.js run "prompt"`
- `node .nano-coding-agent/ai-core/dist/index.js learn "content"`
"""


def install_agent(target_dir: str, hooks: list[str], ides: list[str]) -> None:
    target = Path(target_dir).resolve()
    agent_dir = target / ".nano-coding-agent"
    agent_dir.mkdir(parents=True, exist_ok=True)

    source_ai_core = Path(__file__).resolve().parent.parent / "ai_core"
    dest_ai_core = agent_dir / "ai-core"
    if dest_ai_core.exists():
        shutil.rmtree(dest_ai_core)
    shutil.copytree(str(source_ai_core), str(dest_ai_core))

    agent_yaml = agent_dir / "agent.yaml"
    if not agent_yaml.exists():
        agent_yaml.write_text(DEFAULT_AGENT_YAML, encoding="utf-8")

    if not (dest_ai_core / "node_modules").exists():
        click.echo("Installing ai-core dependencies (requires Node.js/npm)...")
        result = subprocess.run(
            ["npm", "install"],
            cwd=str(dest_ai_core),
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            click.echo(f"[WARNING] npm install failed: {result.stderr}")
            click.echo("[WARNING] Agent will not function until dependencies are installed.")
        else:
            build_result = subprocess.run(
                ["npm", "run", "build"],
                cwd=str(dest_ai_core),
                capture_output=True,
                text=True,
            )
            if build_result.returncode != 0:
                click.echo(f"[WARNING] npm build failed: {build_result.stderr}")

    for hook_name in hooks:
        install_hook(target, hook_name, dest_ai_core)

    for ide in ides:
        install_ide_registration(target, ide)

    click.echo(f"Installed nano-coding-agent to {agent_dir}")


def install_hook(target: Path, hook_name: str, ai_core_dir: Path) -> None:
    hook_dir = target / ".git" / "hooks"
    hook_dir.mkdir(parents=True, exist_ok=True)
    hook_path = hook_dir / hook_name

    script = f"""#!/bin/sh
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"
node "{ai_core_dir / 'dist' / 'index.js'}" hook --name={hook_name}
"""
    hook_path.write_text(script, encoding="utf-8")
    hook_path.chmod(hook_path.stat().st_mode | stat.S_IXUSR)


def install_ide_registration(target: Path, ide: str) -> None:
    if ide == "cursor":
        cursor_dir = target / ".cursor"
        cursor_dir.mkdir(parents=True, exist_ok=True)
        rules_path = cursor_dir / "rules" / "nano-coding-agent.md"
        rules_path.parent.mkdir(parents=True, exist_ok=True)
        rules_path.write_text(CURSOR_RULES, encoding="utf-8")
    elif ide == "claude":
        claude_dir = target / ".claude"
        claude_dir.mkdir(parents=True, exist_ok=True)
        agents_path = claude_dir / "AGENTS.md"
        agents_path.write_text(CLAUDE_REGISTRATION, encoding="utf-8")
    elif ide == "opencode":
        opencode_dir = target / ".opencode"
        opencode_dir.mkdir(parents=True, exist_ok=True)
        skills_path = opencode_dir / "skills" / "nano-coding-agent.md"
        skills_path.parent.mkdir(parents=True, exist_ok=True)
        skills_path.write_text(OPENCODE_REGISTRATION, encoding="utf-8")
