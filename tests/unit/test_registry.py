import tempfile
import unittest
from pathlib import Path

from nano_coding.core.registry import (
    _REGISTRY,
    collect_principle_status,
    register_practice,
    scan_registry,
)


class TestRegistry(unittest.TestCase):
    def tearDown(self) -> None:
        _REGISTRY.clear()

    def test_empty_registry(self) -> None:
        _REGISTRY.clear()
        result = scan_registry()
        self.assertEqual(result, {})

    def test_stacked_decorators(self) -> None:
        _REGISTRY.clear()

        @register_practice(
            "Principle A", {"practice_1": ["nano-coding", "guard", "scan"]}
        )
        @register_practice(
            "Principle A", {"practice_2": ["nano-coding", "guard", "validate"]}
        )
        @register_practice(
            "Principle B", {"practice_x": ["nano-coding", "guard", "install"]}
        )
        def my_func():
            return 42

        self.assertEqual(my_func(), 42)
        self.assertIn("Principle A", _REGISTRY)
        self.assertIn("Principle B", _REGISTRY)
        self.assertEqual(
            _REGISTRY["Principle A"],
            {
                "practice_1": ["nano-coding", "guard", "scan"],
                "practice_2": ["nano-coding", "guard", "validate"],
            },
        )
        self.assertEqual(
            _REGISTRY["Principle B"],
            {"practice_x": ["nano-coding", "guard", "install"]},
        )

    def test_collect_principle_status_mock(self) -> None:
        _REGISTRY.clear()

        @register_practice(
            "Principle A",
            {
                "practice_1": ["nano-coding", "guard", "scan"],
                "practice_2": ["nano-coding", "other", "cmd"],
            },
        )
        def dummy():
            pass

        with tempfile.TemporaryDirectory() as tmp:
            hooks_dir = Path(tmp) / ".git" / "hooks"
            hooks_dir.mkdir(parents=True)
            (hooks_dir / "pre-commit").write_text("run nano-coding guard scan here\n")

            result = collect_principle_status(target_dir=tmp)

        self.assertEqual(
            result["Principle A"]["practice_1"]["command_paths"],
            ["nano-coding", "guard", "scan"],
        )
        self.assertTrue(result["Principle A"]["practice_1"]["in_hooks"])
        self.assertEqual(
            result["Principle A"]["practice_2"]["command_paths"],
            ["nano-coding", "other", "cmd"],
        )
        self.assertFalse(result["Principle A"]["practice_2"]["in_hooks"])
