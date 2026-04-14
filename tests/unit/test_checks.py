"""Unit tests for new suggest checks (Tasks 4-10) and CheckEngine-based checks."""

import os
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path

from nano_coding.core.validator import (
    CheckAgentsLanguage,
    CheckAgentsLength,
    CheckBackgroundContent,
    CheckCommitSize,
    CheckGitignoreTempfiles,
    CheckIndexSummary,
    CheckKnowledgeDir,
    CheckKnowledgeDirExperience,
    CheckPackageManager,
    CheckReadmeI18n,
    CheckSubdirAgents,
    CheckSubdirAgentsOverflow,
    ProtectedDocsCheck,
    build_validation_engine,
)


class TestCheckSubdirAgents(unittest.TestCase):
    """Tests for CheckSubdirAgents."""

    def test_pass_small_project(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "AGENTS.md").write_text("# Project\n")
            result = CheckSubdirAgents().run(root)
            self.assertEqual(result, [])

    def test_fail_large_project_no_subdir_agents(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "AGENTS.md").write_text("# Project\n")
            for i in range(51):
                (root / f"src{i}.py").write_text("pass\n")
            result = CheckSubdirAgents().run(root)
            self.assertEqual(len(result), 1)
            self.assertIn("SUBDIR_AGENTS_MISSING", result[0].rule_id)
            self.assertEqual(result[0].severity, "warning")

    def test_pass_large_project_with_subdir_agents(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "AGENTS.md").write_text("# Project\n")
            subdir = root / "subdir"
            subdir.mkdir()
            (subdir / "AGENTS.md").write_text("# Subdir\n")
            for i in range(51):
                (root / f"src{i}.py").write_text("pass\n")
            result = CheckSubdirAgents().run(root)
            self.assertEqual(result, [])

    def test_fail_long_agents_md(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "AGENTS.md").write_text(
                "\n".join([f"line {i}" for i in range(501)])
            )
            result = CheckSubdirAgents().run(root)
            self.assertEqual(len(result), 1)
            self.assertIn("SUBDIR_AGENTS_MISSING", result[0].rule_id)

    def test_custom_source_file_threshold(self) -> None:
        config = {"checks": {"subdir_agents": {"source_file_threshold": 5}}}
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "AGENTS.md").write_text("# Project\n")
            for i in range(6):
                (root / f"src{i}.py").write_text("pass\n")
            check = CheckSubdirAgents(
                source_file_threshold=config["checks"]["subdir_agents"][
                    "source_file_threshold"
                ]
            )
            result = check.run(root)
            self.assertEqual(len(result), 1)
            self.assertIn("SUBDIR_AGENTS_MISSING", result[0].rule_id)

    def test_custom_agents_line_threshold(self) -> None:
        config = {"checks": {"subdir_agents": {"agents_line_threshold": 10}}}
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "AGENTS.md").write_text("\n".join([f"line {i}" for i in range(11)]))
            check = CheckSubdirAgents(
                agents_line_threshold=config["checks"]["subdir_agents"][
                    "agents_line_threshold"
                ]
            )
            result = check.run(root)
            self.assertEqual(len(result), 1)
            self.assertIn("SUBDIR_AGENTS_MISSING", result[0].rule_id)


class TestCheckIndexSummary(unittest.TestCase):
    """Tests for CheckIndexSummary."""

    def test_pass_with_index_md(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".INDEX.md").write_text("# Index\n")
            result = CheckIndexSummary().run(root)
            self.assertEqual(result, [])

    def test_pass_with_summary_md(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".SUMMARY.md").write_text("# Summary\n")
            result = CheckIndexSummary().run(root)
            self.assertEqual(result, [])

    def test_fail_missing_both(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = CheckIndexSummary().run(root)
            self.assertEqual(len(result), 1)
            self.assertIn("INDEX_SUMMARY_MISSING", result[0].rule_id)
            self.assertEqual(result[0].severity, "warning")
            self.assertIn(".INDEX.md", result[0].message)


class TestCheckKnowledgeDir(unittest.TestCase):
    """Tests for CheckKnowledgeDir and CheckKnowledgeDirExperience."""

    def test_knowledge_dir_pass(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "knowledge").mkdir()
            result = CheckKnowledgeDir().run(root)
            self.assertEqual(result, [])

    def test_knowledge_dir_fail(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = CheckKnowledgeDir().run(root)
            self.assertEqual(len(result), 1)
            self.assertIn("KNOWLEDGE_DIR_MISSING", result[0].rule_id)
            self.assertEqual(result[0].severity, "warning")

    def test_knowledge_dir_experience_pass(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "knowledge").mkdir()
            result = CheckKnowledgeDirExperience().run(root)
            self.assertEqual(result, [])

    def test_knowledge_dir_experience_fail(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = CheckKnowledgeDirExperience().run(root)
            self.assertEqual(len(result), 1)
            self.assertIn("KNOWLEDGE_DIR_MISSING", result[0].rule_id)
            self.assertEqual(result[0].principle, "experience")


class TestCheckSubdirAgentsOverflow(unittest.TestCase):
    """Tests for CheckSubdirAgentsOverflow."""

    def test_pass_small_agents_md(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "AGENTS.md").write_text("# Project\n\n## 基础原则\nSome rules.\n")
            result = CheckSubdirAgentsOverflow().run(root)
            self.assertEqual(result, [])

    def test_fail_too_many_lines(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "AGENTS.md").write_text(
                "\n".join([f"line {i}" for i in range(501)])
            )
            result = CheckSubdirAgentsOverflow().run(root)
            self.assertEqual(len(result), 1)
            self.assertIn("SUBDIR_AGENTS_OVERFLOW", result[0].rule_id)
            self.assertEqual(result[0].severity, "warning")

    def test_fail_too_many_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            blocks = "\n\n".join([f"### Block {i}\nContent." for i in range(21)])
            (root / "AGENTS.md").write_text(f"# Project\n\n{blocks}\n")
            result = CheckSubdirAgentsOverflow().run(root)
            self.assertEqual(len(result), 1)
            self.assertIn("SUBDIR_AGENTS_OVERFLOW", result[0].rule_id)

    def test_pass_with_subdir_agents(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "AGENTS.md").write_text(
                "\n".join([f"line {i}" for i in range(501)])
            )
            subdir = root / "subdir"
            subdir.mkdir()
            (subdir / "AGENTS.md").write_text("# Subdir\n")
            result = CheckSubdirAgentsOverflow().run(root)
            self.assertEqual(result, [])


class TestCheckAgentsLanguage(unittest.TestCase):
    """Tests for CheckAgentsLanguage."""

    def test_pass_single_language_chinese(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "AGENTS.md").write_text("# 项目\n\n## 基础原则\n这是一些规则。\n")
            result = CheckAgentsLanguage().run(root)
            self.assertEqual(result, [])

    def test_pass_single_language_english(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "AGENTS.md").write_text("# Project\n\n## Basics\nSome rules.\n")
            result = CheckAgentsLanguage().run(root)
            self.assertEqual(result, [])

    def test_fail_mixed_language(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            lines = []
            for i in range(20):
                lines.append(f"这是中文 line {i}")
            (root / "AGENTS.md").write_text(
                "# Project\n\n## 基础原则\n" + "\n".join(lines) + "\n"
            )
            result = CheckAgentsLanguage().run(root)
            self.assertEqual(len(result), 1)
            self.assertIn("AGENTS_MIXED_LANGUAGE", result[0].rule_id)
            self.assertEqual(result[0].severity, "warning")

    def test_pass_code_blocks_ignored(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            content = "# 项目\n\n## 基础原则\n```python\nprint('hello world')\n```\n"
            (root / "AGENTS.md").write_text(content)
            result = CheckAgentsLanguage().run(root)
            self.assertEqual(result, [])


class TestCheckReadmeI18n(unittest.TestCase):
    """Tests for CheckReadmeI18n."""

    def test_pass_with_variant_and_link(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "README.md").write_text("# Project\n\n[中文](./README.zh.md)\n")
            (root / "README.zh.md").write_text("# 项目\n")
            result = CheckReadmeI18n().run(root)
            self.assertEqual(result, [])

    def test_fail_missing_variant(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "README.md").write_text("# Project\n")
            result = CheckReadmeI18n().run(root)
            self.assertEqual(len(result), 1)
            self.assertIn("README_I18N_MISSING", result[0].rule_id)
            self.assertEqual(result[0].severity, "warning")

    def test_fail_missing_link(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "README.md").write_text("# Project\n\nSome content.\n")
            (root / "README.zh.md").write_text("# 项目\n")
            result = CheckReadmeI18n().run(root)
            self.assertEqual(len(result), 1)
            self.assertIn("README_I18N_NO_LINK", result[0].rule_id)

    def test_pass_no_readme(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = CheckReadmeI18n().run(root)
            self.assertEqual(result, [])


class TestCheckBackgroundContent(unittest.TestCase):
    """Tests for CheckBackgroundContent."""

    def test_pass_complete_content(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            content = "# Background\n\n愿景、约束、业务逻辑、避坑指南。\n"
            (root / "BACKGROUND.md").write_text(content)
            result = CheckBackgroundContent().run(root)
            self.assertEqual(result, [])

    def test_fail_missing_keywords(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "BACKGROUND.md").write_text("# Background\n\nSome context.\n")
            result = CheckBackgroundContent().run(root)
            self.assertEqual(len(result), 1)
            self.assertIn("BACKGROUND_CONTENT_INCOMPLETE", result[0].rule_id)
            self.assertEqual(result[0].severity, "warning")
            self.assertIn("愿景", result[0].message)

    def test_pass_no_background_md(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = CheckBackgroundContent().run(root)
            self.assertEqual(result, [])


class TestCheckGitignoreTempfiles(unittest.TestCase):
    """Tests for CheckGitignoreTempfiles."""

    def _init_git(self, root: Path) -> None:
        subprocess.run(
            ["git", "init"],
            cwd=str(root),
            capture_output=True,
            check=False,
        )

    def test_pass_no_untracked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._init_git(root)
            result = CheckGitignoreTempfiles().run(root)
            self.assertEqual(result, [])

    def test_warn_sensitive_untracked_no_gitignore(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._init_git(root)
            (root / ".env.local").write_text("SECRET=1\n")
            result = CheckGitignoreTempfiles().run(root)
            self.assertTrue(len(result) >= 1)
            rule_ids = {r.rule_id for r in result}
            self.assertIn("UNTRACKED_SENSITIVE_FILES", rule_ids)
            self.assertIn("GITIGNORE_MISSING", rule_ids)

    def test_pass_with_gitignore(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._init_git(root)
            (root / "normal.txt").write_text("hello\n")
            (root / ".gitignore").write_text("*.log\n")
            result = CheckGitignoreTempfiles().run(root)
            self.assertEqual(result, [])

    def test_warn_large_log_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._init_git(root)
            log_file = root / "debug.log"
            log_file.write_bytes(b"x" * (2 * 1024 * 1024))
            result = CheckGitignoreTempfiles().run(root)
            rule_ids = {r.rule_id for r in result}
            self.assertIn("UNTRACKED_SENSITIVE_FILES", rule_ids)


class TestCheckCommitSize(unittest.TestCase):
    """Tests for CheckCommitSize."""

    def _init_git(self, root: Path) -> None:
        subprocess.run(
            ["git", "init"],
            cwd=str(root),
            capture_output=True,
            check=False,
        )
        subprocess.run(
            ["git", "config", "user.email", "test@test.com"],
            cwd=str(root),
            capture_output=True,
            check=False,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test"],
            cwd=str(root),
            capture_output=True,
            check=False,
        )

    def test_pass_no_staged_changes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._init_git(root)
            result = CheckCommitSize().run(root)
            self.assertEqual(result, [])

    def test_pass_small_commit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._init_git(root)
            f = root / "small.py"
            f.write_text("pass\n")
            subprocess.run(
                ["git", "add", "."],
                cwd=str(root),
                capture_output=True,
                check=False,
            )
            result = CheckCommitSize().run(root)
            self.assertEqual(result, [])

    def test_warn_large_commit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._init_git(root)
            for i in range(12):
                f = root / f"file{i}.py"
                f.write_text(f"value = {i}\n")
            subprocess.run(
                ["git", "add", "."],
                cwd=str(root),
                capture_output=True,
                check=False,
            )
            result = CheckCommitSize().run(root)
            self.assertEqual(len(result), 1)
            self.assertIn("COMMIT_TOO_LARGE", result[0].rule_id)
            self.assertEqual(result[0].severity, "warning")

    def test_custom_max_files_threshold(self) -> None:
        config = {"checks": {"commit_size": {"max_files": 5, "max_insertions": 500}}}
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._init_git(root)
            for i in range(6):
                f = root / f"file{i}.py"
                f.write_text(f"value = {i}\n")
            subprocess.run(
                ["git", "add", "."],
                cwd=str(root),
                capture_output=True,
                check=False,
            )
            check = CheckCommitSize(
                max_files=config["checks"]["commit_size"]["max_files"],
                max_insertions=config["checks"]["commit_size"]["max_insertions"],
            )
            result = check.run(root)
            self.assertEqual(len(result), 1)
            self.assertIn("COMMIT_TOO_LARGE", result[0].rule_id)

    def test_custom_max_insertions_threshold(self) -> None:
        config = {"checks": {"commit_size": {"max_files": 10, "max_insertions": 20}}}
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._init_git(root)
            f = root / "big.py"
            f.write_text("\n".join([f"value = {i}" for i in range(25)]))
            subprocess.run(
                ["git", "add", "."],
                cwd=str(root),
                capture_output=True,
                check=False,
            )
            check = CheckCommitSize(
                max_files=config["checks"]["commit_size"]["max_files"],
                max_insertions=config["checks"]["commit_size"]["max_insertions"],
            )
            result = check.run(root)
            self.assertEqual(len(result), 1)
            self.assertIn("COMMIT_TOO_LARGE", result[0].rule_id)


class TestCheckPackageManager(unittest.TestCase):
    """Tests for CheckPackageManager."""

    def test_pass_no_lock_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = CheckPackageManager().run(root)
            self.assertEqual(result, [])

    def test_pass_matching_commands(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "package-lock.json").write_text("{}\n")
            (root / "README.md").write_text("Install with `npm install`\n")
            result = CheckPackageManager().run(root)
            self.assertEqual(result, [])

    def test_fail_mismatch_npm_vs_pnpm(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "package-lock.json").write_text("{}\n")
            (root / "README.md").write_text("Install with `pnpm install`\n")
            result = CheckPackageManager().run(root)
            self.assertEqual(len(result), 1)
            self.assertIn("PACKAGE_MANAGER_MISMATCH", result[0].rule_id)
            self.assertEqual(result[0].severity, "warning")
            self.assertIn("pnpm", result[0].message)

    def test_fail_mismatch_poetry_vs_pip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "poetry.lock").write_text("[[package]]\n")
            (root / "AGENTS.md").write_text("Run `pip install -r requirements.txt`\n")
            result = CheckPackageManager().run(root)
            self.assertEqual(len(result), 1)
            self.assertIn("PACKAGE_MANAGER_MISMATCH", result[0].rule_id)
            self.assertIn("pip", result[0].message)


class TestCheckAgentsLength(unittest.TestCase):
    """Tests for CheckAgentsLength."""

    def test_pass_short_agents(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "AGENTS.md").write_text("# Project\n\n## 基础原则\n- Rule.\n")
            result = CheckAgentsLength().run(root)
            self.assertEqual(result, [])

    def test_fail_agents_over_1000_lines(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "AGENTS.md").write_text(
                "\n".join([f"line {i}" for i in range(1001)])
            )
            result = CheckAgentsLength().run(root)
            rule_ids = {r.rule_id for r in result}
            self.assertIn("AGENTS_FILE_TOO_LONG", rule_ids)

    def test_fail_block_over_1000_chars(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            body = "x" * 1100
            (root / "AGENTS.md").write_text(f"# Project\n\n### Big Block\n{body}\n")
            result = CheckAgentsLength().run(root)
            rule_ids = {r.rule_id for r in result}
            self.assertIn("PRINCIPLE_BLOCK_TOO_LONG", rule_ids)

    def test_fail_practice_line_over_150_chars(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            long_line = "- " + "x" * 160
            (root / "AGENTS.md").write_text(f"# Project\n\n### 基础原则\n{long_line}\n")
            result = CheckAgentsLength().run(root)
            rule_ids = {r.rule_id for r in result}
            self.assertIn("PRACTICE_LINE_TOO_LONG", rule_ids)

    def test_custom_max_lines_threshold(self) -> None:
        config = {"checks": {"agents_length": {"max_lines": 5}}}
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "AGENTS.md").write_text("\n".join([f"line {i}" for i in range(6)]))
            check = CheckAgentsLength(
                max_lines=config["checks"]["agents_length"]["max_lines"]
            )
            result = check.run(root)
            rule_ids = {r.rule_id for r in result}
            self.assertIn("AGENTS_FILE_TOO_LONG", rule_ids)

    def test_custom_max_principle_chars_threshold(self) -> None:
        config = {"checks": {"agents_length": {"max_principle_chars": 50}}}
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            body = "x" * 60
            (root / "AGENTS.md").write_text(f"# Project\n\n### Big Block\n{body}\n")
            check = CheckAgentsLength(
                max_principle_chars=config["checks"]["agents_length"][
                    "max_principle_chars"
                ]
            )
            result = check.run(root)
            rule_ids = {r.rule_id for r in result}
            self.assertIn("PRINCIPLE_BLOCK_TOO_LONG", rule_ids)

    def test_custom_max_practice_chars_threshold(self) -> None:
        config = {"checks": {"agents_length": {"max_practice_chars": 20}}}
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            long_line = "- " + "x" * 25
            (root / "AGENTS.md").write_text(f"# Project\n\n### 基础原则\n{long_line}\n")
            check = CheckAgentsLength(
                max_practice_chars=config["checks"]["agents_length"][
                    "max_practice_chars"
                ]
            )
            result = check.run(root)
            rule_ids = {r.rule_id for r in result}
            self.assertIn("PRACTICE_LINE_TOO_LONG", rule_ids)


class TestProtectedDocsCheck(unittest.TestCase):
    """Tests for ProtectedDocsCheck."""

    def _init_git(self, root: Path) -> None:
        subprocess.run(
            ["git", "init"],
            cwd=str(root),
            capture_output=True,
            check=False,
        )
        subprocess.run(
            ["git", "config", "user.email", "test@test.com"],
            cwd=str(root),
            capture_output=True,
            check=False,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test"],
            cwd=str(root),
            capture_output=True,
            check=False,
        )

    def test_no_staged_files_pass(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._init_git(root)
            result = ProtectedDocsCheck().run(root)
            self.assertEqual(result, [])

    def test_staged_protected_doc_warn(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._init_git(root)
            (root / "AGENTS.md").write_text("# Project\n")
            subprocess.run(
                ["git", "add", "AGENTS.md"],
                cwd=str(root),
                capture_output=True,
                check=False,
            )
            result = ProtectedDocsCheck().run(root)
            self.assertEqual(len(result), 1)
            self.assertIn("PROTECTED_DOCS_STAGED", result[0].rule_id)
            self.assertEqual(result[0].severity, "warning")
            self.assertIn("AGENTS.md", result[0].message)

    def test_custom_protected_documents(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._init_git(root)
            agent_dir = root / ".nano-coding-agent"
            agent_dir.mkdir()
            config = {"protected_documents": ["CUSTOM.md"]}
            import json

            (agent_dir / "config.json").write_text(json.dumps(config))
            (root / "CUSTOM.md").write_text("# Custom\n")
            subprocess.run(
                ["git", "add", "CUSTOM.md"],
                cwd=str(root),
                capture_output=True,
                check=False,
            )
            result = ProtectedDocsCheck().run(root)
            self.assertEqual(len(result), 1)
            self.assertIn("PROTECTED_DOCS_STAGED", result[0].rule_id)
            self.assertIn("CUSTOM.md", result[0].message)


if __name__ == "__main__":
    unittest.main()
