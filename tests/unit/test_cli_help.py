import unittest
from typing import Generator

import click
from click.testing import CliRunner

from nano_coding.cli import cli as root_cli


def _iter_leaf_commands(
    group: click.Group, prefix: list[str]
) -> Generator[tuple[list[str], click.Command], None, None]:
    ctx = click.Context(group)
    for name in group.list_commands(ctx):
        cmd = group.get_command(ctx, name)
        if cmd is None:
            continue
        path = prefix + [name]
        if isinstance(cmd, click.Group):
            yield from _iter_leaf_commands(cmd, path)
        else:
            yield (path, cmd)


class TestCliHelpCompleteness(unittest.TestCase):
    def test_all_leaf_commands_help_includes_examples(self) -> None:
        runner = CliRunner()
        for path, _cmd in _iter_leaf_commands(root_cli, []):
            with self.subTest(cmd=" ".join(path)):
                result = runner.invoke(root_cli, path + ["--help"])
                self.assertEqual(result.exit_code, 0, msg=result.output)
                output = result.output
                self.assertIn(
                    "Examples:",
                    output,
                    msg=f"Help output missing Examples section for {' '.join(path)}",
                )
                self.assertIn(
                    "nano-coding",
                    output,
                    msg=f"Help output missing command name for {' '.join(path)}",
                )


if __name__ == "__main__":
    unittest.main()
