import os
import stat
import tempfile
import unittest
from pathlib import Path

from guardian.cli import install, merge, validate


class TestCliInstall(unittest.TestCase):
    def test_install_non_git_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(SystemExit) as ctx:
                install(tmp)
            self.assertEqual(ctx.exception.code, 1)

    def test_install_git_directory_copies_hook_and_principles(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            git_dir = root / ".git"
            git_dir.mkdir()

            install(str(root))

            dest_hook = git_dir / "hooks" / "pre-commit"
            self.assertTrue(dest_hook.exists())
            self.assertTrue(os.access(dest_hook, os.X_OK))

            dest_principles = root / "principles" / "core.md"
            self.assertTrue(dest_principles.exists())


class TestCliValidate(unittest.TestCase):
    def test_validate_success_exits_0(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "AGENTS.md").write_text("# Project\n\n## 基础原则\nSome rules.\n")
            pre_commit = root / ".git" / "hooks" / "pre-commit"
            pre_commit.parent.mkdir(parents=True)
            pre_commit.write_text("#!/bin/bash\necho hook\n")
            pre_commit.chmod(pre_commit.stat().st_mode | stat.S_IXUSR)
            (root / "tests").mkdir()
            (root / "tests" / "dummy.py").write_text("pass\n")

            with self.assertRaises(SystemExit) as ctx:
                validate(str(root))
            self.assertEqual(ctx.exception.code, 0)

    def test_validate_blocking_exits_1(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            with self.assertRaises(SystemExit) as ctx:
                validate(str(root))
            self.assertEqual(ctx.exception.code, 1)


class TestCliMerge(unittest.TestCase):
    def test_merge_idempotency(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            principles_file = root / "principles.md"
            target_file = root / "AGENTS.md"

            principles_file.write_text("## Principle A\nBody A\n")
            target_file.write_text(
                "# Agents\n\n## 基础原则\n## Principle A\nOld Body\n"
            )

            merge(str(principles_file), str(target_file))
            first_result = target_file.read_text()

            merge(str(principles_file), str(target_file))
            second_result = target_file.read_text()

            self.assertEqual(first_result, second_result)
