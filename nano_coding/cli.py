import os
from pathlib import Path
from typing import Optional

import click

from nano_coding import __version__
from nano_coding.core.local_skill_loader import discover_local_skills, load_python_skill
from nano_coding.core.project_discovery import find_nearest_agent_dir
from nano_coding.core.version_checker import check_version
from nano_coding.skills.guard import commands as guard_commands
from nano_coding.skills.principle_review import cli as principle_review_cli


class RecursiveHelpGroup(click.Group):
    def format_commands(self, ctx, formatter):
        if not self.commands:
            return

        rows = []
        self._format_commands_recursive(ctx, rows)

        if rows:
            with formatter.section("Commands"):
                formatter.write_dl(rows)

    def _format_commands_recursive(self, ctx, rows, prefix=""):
        for name in self.list_commands(ctx):
            cmd = self.get_command(ctx, name)
            if cmd is None:
                continue

            full_name = f"{prefix}{name}" if prefix else name

            if isinstance(cmd, click.Group):
                help_text = cmd.short_help or cmd.help or ""
                rows.append((full_name, help_text))
                has_subcommands = False
                if hasattr(cmd, "list_commands"):
                    sub_ctx = click.Context(cmd)
                    sub_names = cmd.list_commands(sub_ctx)
                    if sub_names:
                        has_subcommands = True
                    for sub_name in sub_names:
                        sub_cmd = cmd.get_command(sub_ctx, sub_name)
                        if sub_cmd is None:
                            continue
                        sub_help = sub_cmd.short_help or sub_cmd.help or ""
                        if isinstance(sub_cmd, click.Group):
                            rows.append((f"  {full_name} {sub_name}", sub_help))
                        else:
                            opts = self._get_command_options(sub_ctx, sub_cmd)
                            opt_str = f" [{opts}]" if opts else ""
                            rows.append(
                                (f"  {full_name} {sub_name}{opt_str}", sub_help)
                            )
                if not has_subcommands and hasattr(cmd, "get_params"):
                    opts = self._get_command_options(ctx, cmd)
                    if opts:
                        rows[-1] = (f"{full_name} [{opts}]", rows[-1][1])
            else:
                opts = self._get_command_options(ctx, cmd)
                opt_str = f" [{opts}]" if opts else ""
                help_text = cmd.short_help or cmd.help or ""
                rows.append((full_name + opt_str, help_text))

    def _get_command_options(self, ctx, cmd):
        if not hasattr(cmd, "get_params"):
            return ""
        options = []
        for param in cmd.get_params(ctx):
            if isinstance(param, click.Option) and "--help" not in param.opts:
                opt_name = param.opts[0] if param.opts else param.name
                options.append(opt_name)
        return ", ".join(options) if options else ""


@click.group(name="nano-coding", cls=RecursiveHelpGroup)
@click.version_option(version=__version__, prog_name="nano-coding")
def cli() -> None:
    """nano-coding CLI tool for AI coding governance."""


def _make_markdown_skill_command(name: str, body: str) -> click.Command:
    @click.command(name=name)
    def _cmd() -> None:
        click.echo(body)

    return _cmd


def _register_skills() -> None:
    _BUILTIN_SKILLS = {
        "guard": guard_commands,
        "principle-review": principle_review_cli,
    }

    for name, cmd in _BUILTIN_SKILLS.items():
        if isinstance(cmd, click.Group):
            cli.add_command(cmd, name=name)
        elif isinstance(cmd, dict):
            for cmd_name, c in cmd.items():
                if isinstance(c, click.Command):
                    cli.add_command(c, name=cmd_name.replace("_", "-"))
        elif isinstance(cmd, (list, tuple)):
            for c in cmd:
                if isinstance(c, click.Command):
                    cli.add_command(c)

    agent_dir = find_nearest_agent_dir(Path(os.getcwd()))
    if agent_dir is not None:
        check_version(agent_dir)
        for skill in discover_local_skills(agent_dir):
            skill_name = skill["name"]
            metadata = skill["metadata"]
            skill_dir = skill["skill_dir"]
            has_python_module = skill["has_python_module"]

            entrypoint = metadata.get("entrypoint")
            loaded_cmd: Optional[click.Command] = None
            if entrypoint and has_python_module:
                loaded_cmd = load_python_skill(skill_dir, entrypoint)

            if loaded_cmd is None:
                if skill_name in cli.commands:
                    continue
                body = metadata.get("body", "")
                loaded_cmd = _make_markdown_skill_command(skill_name, body)

            if isinstance(loaded_cmd, click.Command):
                cli.add_command(loaded_cmd, name=skill_name)


_register_skills()


def main() -> None:
    cli()


if __name__ == "__main__":
    main()
