import os
import stat
import tempfile
import unittest
from pathlib import Path

from nano_coding.core.agent_installer import install_agent


class TestAgentInstaller(unittest.TestCase):
    def test_install_creates_agent_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            install_agent(str(root), [], [])
            self.assertTrue((root / ".nano-coding-agent").is_dir())
            self.assertTrue((root / ".nano-coding-agent" / "agent.yaml").exists())

    def test_install_selected_hooks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            git_dir = root / ".git"
            git_dir.mkdir()
            install_agent(str(root), ["pre-commit"], [])
            hook = git_dir / "hooks" / "pre-commit"
            self.assertTrue(hook.exists())
            self.assertTrue(os.access(hook, os.X_OK))
            content = hook.read_text(encoding="utf-8")
            self.assertIn("index.js", content)
            self.assertIn("--name=pre-commit", content)

    def test_skips_unselected_hooks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            git_dir = root / ".git"
            git_dir.mkdir()
            install_agent(str(root), [], [])
            self.assertFalse((git_dir / "hooks" / "pre-commit").exists())

    def test_install_cursor_registration(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            install_agent(str(root), [], ["cursor"])
            rules = root / ".cursor" / "rules" / "nano-coding-agent.md"
            self.assertTrue(rules.exists())
            self.assertIn("nano-coding-agent", rules.read_text(encoding="utf-8"))
