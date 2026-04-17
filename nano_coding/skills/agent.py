import subprocess
import sys
from pathlib import Path

import click

from nano_coding.core.agent_installer import install_agent


@click.group(name="agent")
def cli() -> None:
    """Project-level AI agent commands."""
    pass


@cli.command()
@click.argument("target_dir")
@click.option(
    "--hooks",
    default="pre-commit",
    help="Comma-separated list of hooks to install (pre-commit,post-commit,pre-push)",
)
@click.option(
    "--ides",
    default="",
    help="Comma-separated list of IDE registrations (cursor,claude,opencode)",
)
def install(target_dir: str, hooks: str, ides: str) -> None:
    """Install the nano-coding-agent to a project.

    Examples:

        $ nano-coding agent install . --hooks=pre-commit,post-commit
        $ nano-coding agent install . --hooks=pre-commit --ides=cursor,claude
    """
    hook_list = [h.strip() for h in hooks.split(",") if h.strip()]
    ide_list = [i.strip() for i in ides.split(",") if i.strip()]
    install_agent(target_dir, hook_list, ide_list)


def _run_agent_command(project_root: str, command: str, args: list[str]) -> int:
    ai_core = Path(project_root).resolve() / ".nano-coding-agent" / "ai-core"
    index_js = ai_core / "dist" / "index.js"
    if not index_js.exists():
        click.echo("[ERROR] Agent not installed. Run: nano-coding agent install .")
        return 1
    result = subprocess.run(
        ["node", str(index_js), command, *args],
        cwd=project_root,
    )
    return result.returncode


@cli.command()
@click.argument("prompt")
@click.option("--project-root", default=".", help="Project root directory")
def run(prompt: str, project_root: str) -> None:
    """Run the project agent with a prompt.

    Examples:

        $ nano-coding agent run "Review staged changes"
    """
    sys.exit(_run_agent_command(project_root, "run", [prompt]))


@cli.command()
@click.argument("content")
@click.option("--project-root", default=".", help="Project root directory")
def learn(content: str, project_root: str) -> None:
    """Record knowledge via the project agent.

    Examples:

        $ nano-coding agent learn "Always use async/await for I/O"
    """
    sys.exit(_run_agent_command(project_root, "learn", [content]))


@cli.command()
@click.argument("question")
@click.option("--project-root", default=".", help="Project root directory")
def ask(question: str, project_root: str) -> None:
    """Ask the project agent a question.

    Examples:

        $ nano-coding agent ask "What patterns are recorded?"
    """
    sys.exit(_run_agent_command(project_root, "ask", [question]))
