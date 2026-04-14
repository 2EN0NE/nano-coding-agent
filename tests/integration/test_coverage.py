"""Meta test ensuring all @register_practice annotated commands have integration tests.

This module scans the registry for all commands decorated with @register_practice
and verifies that each command path is covered by at least one integration test
module via the TESTED_COMMANDS declaration.
"""

import importlib
import pkgutil
import unittest
from pathlib import Path

from nano_coding.core.registry import scan_registry


class TestIntegrationCoverage(unittest.TestCase):
    """Verify integration test coverage for all registered skills."""

    def test_all_registered_commands_have_integration_tests(self) -> None:
        """Every command registered via @register_practice must be tested."""
        registry = scan_registry()

        # Collect all registered command paths from the registry
        all_commands: set[tuple[str, ...]] = set()
        for principle, practices in registry.items():
            for practice_name, command_paths_list in practices.items():
                for command_paths in command_paths_list:
                    all_commands.add(tuple(command_paths))

        # Collect all declared tested commands from integration test modules
        tested_commands: set[tuple[str, ...]] = set()
        integration_dir = Path(__file__).parent

        for _, name, _ in pkgutil.iter_modules([str(integration_dir)]):
            if name == __name__.split(".")[-1]:
                continue

            module_name = f"tests.integration.{name}"
            try:
                module = importlib.import_module(module_name)
            except Exception as exc:
                self.fail(
                    f"Failed to import integration test module {module_name}: {exc}"
                )

            declared = getattr(module, "TESTED_COMMANDS", [])
            for entry in declared:
                tested_commands.add(tuple(entry))

        missing = all_commands - tested_commands

        if missing:
            formatted = [" ".join(cmd) for cmd in sorted(missing)]
            self.fail(
                "The following @register_practice commands are missing integration tests:\n"
                + "\n".join(f"  - {cmd}" for cmd in formatted)
                + "\n\nAdd integration tests and declare them in the module's "
                "TESTED_COMMANDS list."
            )

    def test_at_least_one_skill_is_registered(self) -> None:
        """Ensure the registry is not empty (sanity check)."""
        registry = scan_registry()
        self.assertTrue(
            registry,
            "Registry is empty - no skills are registered via @register_practice",
        )

        command_count = sum(len(practices) for principle, practices in registry.items())
        self.assertGreater(
            command_count,
            0,
            "No commands found in registry",
        )


if __name__ == "__main__":
    unittest.main()
