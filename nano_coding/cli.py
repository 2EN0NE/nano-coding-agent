import importlib
import pkgutil

import click

import nano_coding.skills


@click.group(name="nano-coding")
@click.version_option(version="0.1.0", prog_name="nano-coding")
def cli() -> None:
    pass


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
