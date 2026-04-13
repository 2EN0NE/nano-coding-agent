import importlib
import pkgutil

import click

import nano_coding.skills


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
@click.version_option(version="0.1.0", prog_name="nano-coding")
def cli() -> None:
    """nano-coding CLI tool for AI coding governance."""


def _register_skills() -> None:
    for _, name, _ in pkgutil.iter_modules(nano_coding.skills.__path__):
        module = importlib.import_module(f"nano_coding.skills.{name}")
        group = getattr(module, "cli", None)
        if isinstance(group, click.Group):
            cli.add_command(group, name=name.replace("_", "-"))


_register_skills()


def main() -> None:
    cli()


if __name__ == "__main__":
    main()
