from __future__ import annotations

import os
import re
import subprocess
import tempfile
from pathlib import Path

from nano_coding.core import config_loader
from nano_coding.core.check_engine import Check, CheckEngine, Issue
from nano_coding.core.principles import extractPrincipleBlocks

DEFAULT_RULES: list[str] = []

EXCLUDE_DIRS = {
    ".git",
    "node_modules",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    "dist",
    "build",
    ".opencode",
}

FILE_EXTENSIONS = {
    ".py",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".rs",
    ".go",
    ".java",
    ".md",
    ".yml",
    ".yaml",
    ".json",
    ".toml",
}

LOCK_FILES = {
    "package-lock.json",
    "Cargo.lock",
    "Pipfile.lock",
    "poetry.lock",
    "yarn.lock",
    "pnpm-lock.yaml",
}

# Principle metadata for human-readable output
_PRINCIPLES = {
    "core_principles": {
        "title": "最重要原则：核心指导原则需要由人类审核",
        "explanation": "对于重要提供AGENT指导的文档文件，必须用主要编程用户的熟悉语言编写，由人工审核。AGENTS.md 是 AI 行动的唯一事实来源，缺失或内容不完整将导致 Agent 无法遵循项目规范。",
    },
    "guardrails": {
        "title": "行为边界与'防呆'原则 (Guardrails & Boundaries)",
        "explanation": "明确告诉 AI '绝对不要做什么'，比告诉它'要做什么'更有效。通过设置明确边界，防止 Agent 产生不可逆的错误操作。",
    },
    "tdd_first": {
        "title": "测试先行原则（TDD First）",
        "explanation": "每次行动，先设计与思考如何测试，并先编写测试，在AGENTS.md或README.md中让智能体知道如何测试自己的产出。测试是代码质量的最终保障。",
    },
    "tdd_separation": {
        "title": "TDD先行",
        "explanation": "测试一定要区分集成测试与单元测试，测试文件夹下通过二级目录区分不同类型。只有严格分离，才能在不同阶段执行合适的测试策略。",
    },
    "background": {
        "title": "项目背景文档 (BACKGROUND.md)",
        "explanation": "每个项目应有独立的背景文档，让 AI Agent 在没有人类语境的情况下也能理解项目的存在理由，包含项目愿景、核心约束、业务逻辑、避坑指南。",
    },
    "workflow": {
        "title": "结构化任务流原则 (Workflow Structure)",
        "explanation": "强制要求 AI 在执行前先进行思考与规划，同时保持工作区的整洁。临时文档应在任务完成后清理，避免对后续 Agent 产生干扰。",
    },
    "length_limit": {
        "title": "控制长度",
        "explanation": "每保留必不可少的指令，剔除所有'废话'。条描述建议在150行以内，每个文件控制在1000行以内，以保持文档和代码的可读性、可维护性。",
    },
    "progressive_disclosure": {
        "title": "渐进式披露原则 (Progressive Disclosure)",
        "explanation": "不要在根目录的 AGENTS.md 里堆砌所有子模块的细节。通过目录分权、外部引用和知识目录保持文档可读性。",
    },
    "experience": {
        "title": "经验积累",
        "explanation": "每次用户对Agents结果的有效反馈，需提炼经验，补充到相应的地方。",
    },
    "doc_language": {
        "title": "文档语言",
        "explanation": "项目文档应以主要开发人员最熟悉的语言编写，鼓励进行多语言文档设置。",
    },
    "git_commit": {
        "title": "Git Commit规范",
        "explanation": "采用规范的提交格式和合理的提交粒度，确保版本历史清晰可维护。",
    },
}


def issue_to_dict(issue: Issue) -> dict[str, str]:
    meta = _PRINCIPLES.get(issue.principle, {})
    return {
        "message": issue.message,
        "principle": meta.get("title", issue.principle),
        "explanation": meta.get("explanation", ""),
    }


class AgentsMdExistsCheck(Check):
    name = "agents_md_exists"
    principle = "core_principles"
    practice = "AGENTS.md存在"
    severity = "blocking"
    requires_llm = False

    def run(self, project_root: Path) -> list[Issue]:
        if not (project_root / "AGENTS.md").exists():
            return [
                Issue(
                    path=None,
                    line=None,
                    rule_id="AGENTS_MD_MISSING",
                    message="AGENTS.md not found in project root.",
                    principle=self.principle,
                    practice=self.practice,
                    severity=self.severity,
                )
            ]
        return []


class AgentsMdHasSectionCheck(Check):
    name = "agents_md_has_section"
    principle = "core_principles"
    practice = "基础原则章节"
    severity = "blocking"
    requires_llm = False

    def run(self, project_root: Path) -> list[Issue]:
        agents_md = project_root / "AGENTS.md"
        if not agents_md.exists():
            return []
        content = agents_md.read_text(encoding="utf-8")
        if "## 基础原则" not in content:
            return [
                Issue(
                    path="AGENTS.md",
                    line=None,
                    rule_id="AGENTS_MD_NO_SECTION",
                    message='AGENTS.md is missing the required "## 基础原则" section.',
                    principle=self.principle,
                    practice=self.practice,
                    severity=self.severity,
                )
            ]
        return []


class ForbiddenDirsCheck(Check):
    name = "forbidden_dirs"
    principle = "guardrails"
    practice = "禁止目录"
    severity = "blocking"
    requires_llm = False

    def run(self, project_root: Path) -> list[Issue]:
        issues = []
        forbidden = ["templates", "scripts"]
        for d in forbidden:
            if (project_root / d).is_dir():
                issues.append(
                    Issue(
                        path=d,
                        line=None,
                        rule_id="FORBIDDEN_DIR",
                        message=f'Forbidden directory at root: {d}/ (violates "生成项目的禁止规则")',
                        principle=self.principle,
                        practice=self.practice,
                        severity=self.severity,
                    )
                )
        return issues


class PreCommitHookCheck(Check):
    name = "pre_commit_hook"
    principle = "guardrails"
    practice = "pre-commit钩子"
    severity = "warning"
    requires_llm = False

    def run(self, project_root: Path) -> list[Issue]:
        pre_commit = project_root / ".git" / "hooks" / "pre-commit"
        if not pre_commit.exists():
            return [
                Issue(
                    path=".git/hooks/pre-commit",
                    line=None,
                    rule_id="PRE_COMMIT_MISSING",
                    message="Git pre-commit hook is not installed (.git/hooks/pre-commit missing).",
                    principle=self.principle,
                    practice=self.practice,
                    severity=self.severity,
                )
            ]
        if not os.access(pre_commit, os.X_OK):
            return [
                Issue(
                    path=".git/hooks/pre-commit",
                    line=None,
                    rule_id="PRE_COMMIT_NOT_EXECUTABLE",
                    message="Git pre-commit hook exists but is not executable.",
                    principle=self.principle,
                    practice=self.practice,
                    severity=self.severity,
                )
            ]
        return []


class TempDocsCheck(Check):
    name = "temp_docs"
    principle = "workflow"
    practice = "临时文档清理"
    severity = "warning"
    requires_llm = False

    def run(self, project_root: Path) -> list[Issue]:
        issues = []
        for temp_doc in ["TODO.md", "PROGRESS.md"]:
            if (project_root / temp_doc).exists():
                issues.append(
                    Issue(
                        path=temp_doc,
                        line=None,
                        rule_id="TEMP_DOC_FOUND",
                        message=f"{temp_doc} found at project root. Consider removing it after task completion.",
                        principle=self.principle,
                        practice=self.practice,
                        severity=self.severity,
                    )
                )
        return issues


class TestsExistCheck(Check):
    name = "tests_exist"
    principle = "tdd_first"
    practice = "测试存在"
    severity = "warning"
    requires_llm = False

    def run(self, project_root: Path) -> list[Issue]:
        test_indicators = ["tests", "test", "spec"]
        for indicator in test_indicators:
            if (project_root / indicator).is_dir():
                return []
            if (
                list(project_root.rglob(f"*{indicator}*.py"))
                or list(project_root.rglob(f"*{indicator}*.ts"))
                or list(project_root.rglob(f"*{indicator}*.rs"))
            ):
                return []
        return [
            Issue(
                path=None,
                line=None,
                rule_id="NO_TESTS",
                message="No tests directory or test files detected.",
                principle=self.principle,
                practice=self.practice,
                severity=self.severity,
            )
        ]


class FileLengthCheck(Check):
    name = "file_length"
    principle = "length_limit"
    practice = "文件长度限制"
    severity = "blocking"
    requires_llm = False

    def __init__(self, max_lines: int = 1000, exclude_dirs: set[str] | None = None):
        self.max_lines = max_lines
        self.exclude_dirs = exclude_dirs or set()

    def run(self, project_root: Path) -> list[Issue]:
        issues = []
        for path in project_root.rglob("*.md"):
            if not path.is_file():
                continue
            try:
                relative = path.relative_to(project_root)
            except ValueError:
                continue
            if any(part in self.exclude_dirs for part in relative.parts):
                continue
            try:
                with path.open("rb") as f:
                    line_count = sum(1 for _ in f)
            except Exception:
                continue
            if line_count > self.max_lines:
                issues.append(
                    Issue(
                        path=str(relative),
                        line=None,
                        rule_id="FILE_TOO_LONG",
                        message=f"Document exceeds {self.max_lines} lines ({line_count}): {relative}",
                        principle=self.principle,
                        practice=self.practice,
                        severity=self.severity,
                    )
                )
        return issues


class AgentsAbortCheck(Check):
    name = "agents_abort"
    principle = "guardrails"
    practice = "AGENTS_ABORT.md"
    severity = "blocking"
    requires_llm = False

    def run(self, project_root: Path) -> list[Issue]:
        agents_abort = project_root / "AGENTS_ABORT.md"
        banned_behaviors = project_root / "BANNED-AGENT-BEHAVIORS.md"

        if not agents_abort.exists() and not banned_behaviors.exists():
            return [
                Issue(
                    path=None,
                    line=None,
                    rule_id="AGENTS_ABORT_MISSING",
                    message="AGENTS_ABORT.md (or BANNED-AGENT-BEHAVIORS.md) not found.",
                    principle=self.principle,
                    practice=self.practice,
                    severity=self.severity,
                )
            ]

        existing_file = agents_abort if agents_abort.exists() else banned_behaviors
        content = existing_file.read_text(encoding="utf-8").strip()
        if not content:
            return [
                Issue(
                    path=str(existing_file.relative_to(project_root)),
                    line=None,
                    rule_id="AGENTS_ABORT_EMPTY",
                    message=f"{existing_file.name} is empty.",
                    principle=self.principle,
                    practice=self.practice,
                    severity=self.severity,
                )
            ]
        return []


class BackgroundMdCheck(Check):
    name = "background_md"
    principle = "background"
    practice = "BACKGROUND.md"
    severity = "blocking"
    requires_llm = False

    def run(self, project_root: Path) -> list[Issue]:
        if not (project_root / "BACKGROUND.md").exists():
            return [
                Issue(
                    path=None,
                    line=None,
                    rule_id="BACKGROUND_MISSING",
                    message="BACKGROUND.md not found in project root.",
                    principle=self.principle,
                    practice=self.practice,
                    severity=self.severity,
                )
            ]
        return []


class TestSeparationCheck(Check):
    name = "test_separation"
    principle = "tdd_separation"
    practice = "测试分离"
    severity = "blocking"
    requires_llm = False

    def run(self, project_root: Path) -> list[Issue]:
        issues = []
        unit_dir = project_root / "tests" / "unit"
        integration_dir = project_root / "tests" / "integration"

        if not unit_dir.is_dir():
            issues.append(
                Issue(
                    path=None,
                    line=None,
                    rule_id="MISSING_UNIT_DIR",
                    message="Missing tests/unit/ directory (required for test type separation).",
                    principle=self.principle,
                    practice=self.practice,
                    severity=self.severity,
                )
            )
        if not integration_dir.is_dir():
            issues.append(
                Issue(
                    path=None,
                    line=None,
                    rule_id="MISSING_INTEGRATION_DIR",
                    message="Missing tests/integration/ directory (required for test type separation).",
                    principle=self.principle,
                    practice=self.practice,
                    severity=self.severity,
                )
            )
        return issues


class TestCommandsCheck(Check):
    name = "test_commands"
    principle = "tdd_first"
    practice = "测试命令文档"
    severity = "blocking"
    requires_llm = False

    TEST_COMMAND_PATTERNS = [
        r"pytest\s+[-\w]",
        r"npm\s+test",
        r"yarn\s+test",
        r"pnpm\s+test",
        r"cargo\s+test",
        r"go\s+test",
        r"mvn\s+test",
        r"gradle\s+test",
        r"dotnet\s+test",
        r"python\s+-m\s+(pytest|unittest)",
    ]

    def run(self, project_root: Path) -> list[Issue]:
        readme = project_root / "README.md"
        agents = project_root / "AGENTS.md"

        combined_content = ""
        if readme.exists():
            combined_content += readme.read_text(encoding="utf-8")
        if agents.exists():
            combined_content += agents.read_text(encoding="utf-8")

        for pattern in self.TEST_COMMAND_PATTERNS:
            if re.search(pattern, combined_content):
                return []

        return [
            Issue(
                path=None,
                line=None,
                rule_id="NO_TEST_COMMANDS",
                message="No specific test commands found in README.md or AGENTS.md. Document commands like 'pytest -v' or 'npm test'.",
                principle=self.principle,
                practice=self.practice,
                severity=self.severity,
            )
        ]


def _has_subdir_agents(project_root: Path) -> bool:
    for path in project_root.rglob("AGENTS.md"):
        if path.parent != project_root:
            return True
    return False


def _count_source_files(project_root: Path) -> int:
    test_dirs = {"tests", "test", "spec"}
    count = 0
    for path in project_root.rglob("*"):
        if not path.is_file():
            continue
        try:
            relative = path.relative_to(project_root)
        except ValueError:
            continue
        if any(part in EXCLUDE_DIRS or part in test_dirs for part in relative.parts):
            continue
        if path.suffix not in FILE_EXTENSIONS:
            continue
        if path.name in LOCK_FILES:
            continue
        count += 1
    return count


class CheckSubdirAgents(Check):
    name = "subdir_agents"
    principle = "progressive_disclosure"
    practice = "目录分权"
    severity = "warning"
    requires_llm = False

    def run(self, project_root: Path) -> list[Issue]:
        agents_md = project_root / "AGENTS.md"
        agents_lines = 0
        if agents_md.exists():
            with agents_md.open("rb") as f:
                agents_lines = sum(1 for _ in f)
        if _count_source_files(project_root) > 50 or agents_lines > 500:
            if not _has_subdir_agents(project_root):
                return [
                    Issue(
                        path=None,
                        line=None,
                        rule_id="SUBDIR_AGENTS_MISSING",
                        message="Project is large (>50 source files or AGENTS.md >500 lines) but no sub-directory AGENTS.md found.",
                        principle=self.principle,
                        practice=self.practice,
                        severity=self.severity,
                    )
                ]
        return []


class CheckIndexSummary(Check):
    name = "index_summary"
    principle = "progressive_disclosure"
    practice = "外部引用"
    severity = "warning"
    requires_llm = False

    def run(self, project_root: Path) -> list[Issue]:
        if (
            not (project_root / ".INDEX.md").exists()
            and not (project_root / ".SUMMARY.md").exists()
        ):
            return [
                Issue(
                    path=None,
                    line=None,
                    rule_id="INDEX_SUMMARY_MISSING",
                    message="Neither .INDEX.md nor .SUMMARY.md found in project root. Consider adding an architecture overview document.",
                    principle=self.principle,
                    practice=self.practice,
                    severity=self.severity,
                )
            ]
        return []


class CheckKnowledgeDir(Check):
    name = "knowledge_dir"
    principle = "progressive_disclosure"
    practice = "AGENTS可读"
    severity = "warning"
    requires_llm = False

    def run(self, project_root: Path) -> list[Issue]:
        if not (project_root / "knowledge").is_dir():
            return [
                Issue(
                    path=None,
                    line=None,
                    rule_id="KNOWLEDGE_DIR_MISSING",
                    message="knowledge/ directory not found in project root. Consider creating one for accumulated learnings.",
                    principle=self.principle,
                    practice=self.practice,
                    severity=self.severity,
                )
            ]
        return []


class CheckKnowledgeDirExperience(CheckKnowledgeDir):
    name = "knowledge_dir_experience"
    principle = "experience"
    practice = "集中收集"


class CheckSubdirAgentsOverflow(Check):
    name = "subdir_agents_overflow"
    principle = "experience"
    practice = "分散规整"
    severity = "warning"
    requires_llm = False

    def run(self, project_root: Path) -> list[Issue]:
        agents_md = project_root / "AGENTS.md"
        if not agents_md.exists():
            return []
        content = agents_md.read_text(encoding="utf-8")
        lines = content.splitlines()
        blocks = extractPrincipleBlocks(content)
        if len(lines) > 500 or len(blocks) > 20:
            if not _has_subdir_agents(project_root):
                return [
                    Issue(
                        path=None,
                        line=None,
                        rule_id="SUBDIR_AGENTS_OVERFLOW",
                        message="AGENTS.md is large (>500 lines or >20 principle sections) but no sub-directory AGENTS.md found for overflow.",
                        principle=self.principle,
                        practice=self.practice,
                        severity=self.severity,
                    )
                ]
        return []


class CheckAgentsLanguage(Check):
    name = "agents_language"
    principle = "doc_language"
    practice = "权威文档（AGENTS.md）保持必须单一语言"
    severity = "warning"
    requires_llm = False

    def run(self, project_root: Path) -> list[Issue]:
        agents_md = project_root / "AGENTS.md"
        if not agents_md.exists():
            return []
        lines = agents_md.read_text(encoding="utf-8").splitlines()
        in_code = False
        non_trivial = 0
        mixed = 0
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("```"):
                in_code = not in_code
                continue
            if in_code:
                continue
            if not stripped:
                continue
            if stripped.startswith("#") or stripped.startswith("---"):
                continue
            non_trivial += 1
            has_cjk = bool(re.search(r"[\u4e00-\u9fff]", line))
            has_latin = bool(re.search(r"[A-Za-z]", line))
            if has_cjk and has_latin:
                mixed += 1
        if non_trivial > 0 and mixed / non_trivial > 0.30:
            return [
                Issue(
                    path="AGENTS.md",
                    line=None,
                    rule_id="AGENTS_MIXED_LANGUAGE",
                    message=f"AGENTS.md appears to use mixed scripts ({mixed}/{non_trivial} lines). Keep the authoritative document in a single language.",
                    principle=self.principle,
                    practice=self.practice,
                    severity=self.severity,
                )
            ]
        return []


class CheckReadmeI18n(Check):
    name = "readme_i18n"
    principle = "doc_language"
    practice = "多语言文档关联"
    severity = "warning"
    requires_llm = False

    def run(self, project_root: Path) -> list[Issue]:
        readme = project_root / "README.md"
        if not readme.exists():
            return []
        variants = list(project_root.glob("README.*.md"))
        if not variants:
            return [
                Issue(
                    path="README.md",
                    line=None,
                    rule_id="README_I18N_MISSING",
                    message="README.md exists but no translated variants (README.<lang>.md) found.",
                    principle=self.principle,
                    practice=self.practice,
                    severity=self.severity,
                )
            ]
        top_lines = readme.read_text(encoding="utf-8").splitlines()[:10]
        has_link = any(re.search(r"README\.[a-z]{2}\.md", line) for line in top_lines)
        if not has_link:
            return [
                Issue(
                    path="README.md",
                    line=None,
                    rule_id="README_I18N_NO_LINK",
                    message="README.md missing language link at the top (expected reference to README.<lang>.md).",
                    principle=self.principle,
                    practice=self.practice,
                    severity=self.severity,
                )
            ]
        return []


class CheckBackgroundContent(Check):
    name = "background_content"
    principle = "background"
    practice = "内容应包含：项目愿景、核心约束、业务逻辑、避坑指南"
    severity = "warning"
    requires_llm = False

    def run(self, project_root: Path) -> list[Issue]:
        bg = project_root / "BACKGROUND.md"
        if not bg.exists():
            return []
        content = bg.read_text(encoding="utf-8")
        keywords = ["愿景", "约束", "业务逻辑", "避坑"]
        missing = [kw for kw in keywords if kw not in content]
        if missing:
            return [
                Issue(
                    path="BACKGROUND.md",
                    line=None,
                    rule_id="BACKGROUND_CONTENT_INCOMPLETE",
                    message=f"BACKGROUND.md missing recommended keywords: {', '.join(missing)}.",
                    principle=self.principle,
                    practice=self.practice,
                    severity=self.severity,
                )
            ]
        return []


class CheckGitignoreTempfiles(Check):
    name = "gitignore_tempfiles"
    principle = "git_commit"
    practice = "提交前准备"
    severity = "warning"
    requires_llm = False

    SENSITIVE_PREFIXES = (".env", "credentials", "secret")
    SENSITIVE_SUFFIXES = (".key", ".pem", ".p12", ".log")
    EXACT_NAMES = ("id_rsa",)

    def run(self, project_root: Path) -> list[Issue]:
        try:
            proc = subprocess.run(
                ["git", "status", "--short"],
                cwd=str(project_root),
                capture_output=True,
                text=True,
                check=False,
            )
        except Exception:
            return []
        if proc.returncode != 0:
            return []
        untracked_files: list[str] = []
        for line in proc.stdout.splitlines():
            if line.startswith("?? "):
                untracked_files.append(line[3:].strip())
        issues: list[Issue] = []
        sensitive: list[str] = []
        for f in untracked_files:
            name = os.path.basename(f)
            path = project_root / f
            is_sensitive = False
            if name in self.EXACT_NAMES:
                is_sensitive = True
            if not is_sensitive and any(
                name.startswith(p) or name.startswith("." + p)
                for p in self.SENSITIVE_PREFIXES
            ):
                is_sensitive = True
            if not is_sensitive and any(
                name.endswith(suf) for suf in self.SENSITIVE_SUFFIXES
            ):
                if name.endswith(".log") and path.is_file():
                    try:
                        if path.stat().st_size > 1_048_576:
                            is_sensitive = True
                    except Exception:
                        pass
                else:
                    is_sensitive = True
            if is_sensitive:
                sensitive.append(f)
        if sensitive:
            issues.append(
                Issue(
                    path=None,
                    line=None,
                    rule_id="UNTRACKED_SENSITIVE_FILES",
                    message=f"Untracked sensitive/temp files detected: {', '.join(sensitive)}. Consider adding them to .gitignore.",
                    principle=self.principle,
                    practice=self.practice,
                    severity=self.severity,
                )
            )
        if untracked_files and not (project_root / ".gitignore").exists():
            issues.append(
                Issue(
                    path=None,
                    line=None,
                    rule_id="GITIGNORE_MISSING",
                    message=".gitignore is missing while untracked files exist. Consider creating one.",
                    principle=self.principle,
                    practice=self.practice,
                    severity=self.severity,
                )
            )
        return issues


class CheckCommitSize(Check):
    name = "commit_size"
    principle = "git_commit"
    practice = "提交粒度"
    severity = "warning"
    requires_llm = False

    def run(self, project_root: Path) -> list[Issue]:
        try:
            proc = subprocess.run(
                ["git", "diff", "--cached", "--stat"],
                cwd=str(project_root),
                capture_output=True,
                text=True,
                check=False,
            )
        except Exception:
            return []
        if proc.returncode != 0:
            return []
        output = proc.stdout.strip()
        if not output:
            return []
        m = re.search(r"(\d+)\s+files? changed,\s+(\d+)\s+insertions?\(\+\)", output)
        if not m:
            return []
        files_changed = int(m.group(1))
        insertions = int(m.group(2))
        if files_changed > 10 or insertions > 500:
            return [
                Issue(
                    path=None,
                    line=None,
                    rule_id="COMMIT_TOO_LARGE",
                    message=f"Staged commit is large ({files_changed} files, {insertions}+ lines). Consider splitting into smaller commits.",
                    principle=self.principle,
                    practice=self.practice,
                    severity=self.severity,
                )
            ]
        return []


class CheckPackageManager(Check):
    name = "package_manager"
    principle = "tdd_first"
    practice = "环境特异性"
    severity = "warning"
    requires_llm = False

    LOCK_MANAGER_MAP = {
        "package-lock.json": "npm",
        "pnpm-lock.yaml": "pnpm",
        "yarn.lock": "yarn",
        "Cargo.lock": "cargo",
        "poetry.lock": "poetry",
        "Pipfile.lock": "pipenv",
    }

    BAD_PATTERNS = {
        "npm": [r"\bpnpm\s+install\b", r"\byarn\s+install\b", r"\byarn\s+add\b"],
        "pnpm": [
            r"\bnpm\s+install\b",
            r"\byarn\s+install\b",
            r"\byarn\s+add\b",
            r"\bnpm\s+ci\b",
        ],
        "yarn": [r"\bnpm\s+install\b", r"\bpnpm\s+install\b", r"\bnpm\s+ci\b"],
        "cargo": [
            r"\bnpm\s+install\b",
            r"\byarn\s+install\b",
            r"\bpnpm\s+install\b",
            r"\bpip\s+install\b",
            r"\bpoetry\s+install\b",
            r"\bpipenv\s+install\b",
        ],
        "poetry": [
            r"\bpip\s+install\b",
            r"\bpipenv\s+install\b",
            r"\bnpm\s+install\b",
            r"\byarn\s+install\b",
            r"\bpnpm\s+install\b",
        ],
        "pipenv": [
            r"\bpip\s+install\b",
            r"\bpoetry\s+install\b",
            r"\bnpm\s+install\b",
            r"\byarn\s+install\b",
            r"\bpnpm\s+install\b",
        ],
    }

    def run(self, project_root: Path) -> list[Issue]:
        detected: list[str] = []
        for lock_file, manager in self.LOCK_MANAGER_MAP.items():
            if (project_root / lock_file).exists():
                detected.append(manager)
        if not detected:
            return []
        combined = ""
        for doc in (project_root / "README.md", project_root / "AGENTS.md"):
            if doc.exists():
                combined += doc.read_text(encoding="utf-8")
        if not combined:
            return []
        for manager in detected:
            for pattern in self.BAD_PATTERNS.get(manager, []):
                if re.search(pattern, combined):
                    return [
                        Issue(
                            path=None,
                            line=None,
                            rule_id="PACKAGE_MANAGER_MISMATCH",
                            message=f"Lock file suggests {manager}, but docs contain inconsistent install command matching /{pattern}/.",
                            principle=self.principle,
                            practice=self.practice,
                            severity=self.severity,
                        )
                    ]
        return []


class CheckAgentsLength(Check):
    name = "agents_length"
    principle = "length_limit"
    practice = "控制长度"
    severity = "warning"
    requires_llm = False

    def run(self, project_root: Path) -> list[Issue]:
        agents_md = project_root / "AGENTS.md"
        if not agents_md.exists():
            return []
        issues: list[Issue] = []
        lines = agents_md.read_text(encoding="utf-8").splitlines()
        if len(lines) > 1000:
            issues.append(
                Issue(
                    path="AGENTS.md",
                    line=None,
                    rule_id="AGENTS_FILE_TOO_LONG",
                    message=f"AGENTS.md exceeds 1000 lines ({len(lines)}).",
                    principle=self.principle,
                    practice=self.practice,
                    severity=self.severity,
                )
            )
        blocks = extractPrincipleBlocks(agents_md.read_text(encoding="utf-8"))
        for block in blocks:
            total_chars = len(block.title) + len(block.body)
            if total_chars > 1000:
                issues.append(
                    Issue(
                        path="AGENTS.md",
                        line=None,
                        rule_id="PRINCIPLE_BLOCK_TOO_LONG",
                        message=f'Principle block "{block.title}" exceeds 1000 chars ({total_chars}).',
                        principle=self.principle,
                        practice=self.practice,
                        severity=self.severity,
                    )
                )
            for line in block.body.splitlines():
                if line.strip().startswith("- "):
                    if len(line) > 150:
                        issues.append(
                            Issue(
                                path="AGENTS.md",
                                line=None,
                                rule_id="PRACTICE_LINE_TOO_LONG",
                                message=f"Practice line exceeds 150 chars: {line[:80]}...",
                                principle=self.principle,
                                practice=self.practice,
                                severity=self.severity,
                            )
                        )
        return issues


def build_validation_engine(
    max_lines: int = 1000,
    exclude_dirs: set[str] | None = None,
) -> CheckEngine:
    """Build and return a CheckEngine with all validation checks registered."""
    engine = CheckEngine()
    engine.register(AgentsMdExistsCheck())
    engine.register(AgentsMdHasSectionCheck())
    engine.register(ForbiddenDirsCheck())
    engine.register(PreCommitHookCheck())
    engine.register(TempDocsCheck())
    engine.register(TestsExistCheck())
    engine.register(FileLengthCheck(max_lines=max_lines, exclude_dirs=exclude_dirs))
    engine.register(AgentsAbortCheck())
    engine.register(BackgroundMdCheck())
    engine.register(TestSeparationCheck())
    engine.register(TestCommandsCheck())
    engine.register(CheckSubdirAgents())
    engine.register(CheckIndexSummary())
    engine.register(CheckKnowledgeDir())
    engine.register(CheckKnowledgeDirExperience())
    engine.register(CheckSubdirAgentsOverflow())
    engine.register(CheckAgentsLanguage())
    engine.register(CheckReadmeI18n())
    engine.register(CheckBackgroundContent())
    engine.register(CheckGitignoreTempfiles())
    engine.register(CheckCommitSize())
    engine.register(CheckPackageManager())
    engine.register(CheckAgentsLength())
    return engine


def validate_project(
    project_root: str,
    max_lines: int = 1000,
    check_forbidden_dirs: bool = True,
    check_agents_abort: bool = False,
    check_background: bool = False,
    check_test_separation: bool = False,
    check_test_commands: bool = False,
) -> dict:
    root = Path(project_root).resolve()

    config = config_loader.resolve_config(root)
    validate_config = config.get("validate", {})

    if isinstance(validate_config.get("max_lines"), int):
        max_lines = validate_config["max_lines"]

    rules = list(DEFAULT_RULES)
    if isinstance(validate_config.get("rules"), list):
        rules.extend(validate_config["rules"])

    exclude_dirs = set(EXCLUDE_DIRS)
    if isinstance(validate_config.get("ignore_dirs"), list):
        exclude_dirs.update(validate_config["ignore_dirs"])

    engine = build_validation_engine(max_lines=max_lines, exclude_dirs=exclude_dirs)

    names = [
        "agents_md_exists",
        "agents_md_has_section",
        "pre_commit_hook",
        "temp_docs",
        "tests_exist",
        "file_length",
    ]
    if check_forbidden_dirs:
        names.append("forbidden_dirs")
    if check_agents_abort:
        names.append("agents_abort")
    if check_background:
        names.append("background_md")
    if check_test_separation:
        names.append("test_separation")
    if check_test_commands:
        names.append("test_commands")

    results = engine.run_all(root, names=names, llm=False)

    blocking: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []

    for check_name, issues in results.items():
        for issue in issues:
            issue_dict = issue_to_dict(issue)
            if issue.severity == "blocking":
                blocking.append(issue_dict)
            else:
                warnings.append(issue_dict)

    success = len(blocking) == 0
    return {
        "success": success,
        "blocking": blocking,
        "warnings": warnings,
        "rules": rules,
    }


def format_validation_report(result: dict) -> str:
    """Format validation result into a human-readable report string."""
    lines: list[str] = []
    blocking = result.get("blocking", [])
    warnings = result.get("warnings", [])

    if not blocking and not warnings:
        lines.append("[PASS] All checks passed. Project looks good!")
        return "\n".join(lines)

    if blocking and warnings:
        lines.append(f"[BLOCKING] {len(blocking)} issue(s) found")
        lines.append(f"[WARNING] {len(warnings)} issue(s) found")
    elif blocking:
        lines.append(f"[BLOCKING] {len(blocking)} issue(s) found")
    else:
        lines.append(f"[WARNING] {len(warnings)} issue(s) found")

    if blocking:
        lines.append("")
        lines.append("═" * 50)
        lines.append(" BLOCKING ISSUES ")
        lines.append("═" * 50)
        for idx, issue in enumerate(blocking, 1):
            lines.append(f"\n[{idx}] {issue['message']}")
            lines.append(f"    原则：{issue['principle']}")
            lines.append(f"    说明：{issue['explanation']}")

    if warnings:
        lines.append("")
        lines.append("─" * 50)
        lines.append(" WARNINGS ")
        lines.append("─" * 50)
        for idx, issue in enumerate(warnings, 1):
            lines.append(f"\n[{idx}] {issue['message']}")
            lines.append(f"    原则：{issue['principle']}")
            lines.append(f"    说明：{issue['explanation']}")

    lines.append("")
    lines.append("─" * 50)
    if blocking:
        lines.append("Result: FAILED (blocking issues must be resolved)")
    else:
        lines.append("Result: PASSED with warnings")
    lines.append("─" * 50)

    return "\n".join(lines)


def show_report_interactively(report: str) -> None:
    """Display the report using a pager (less-style interaction)."""
    with tempfile.NamedTemporaryFile(mode="w+", suffix=".txt", delete=False) as f:
        f.write(report)
        f.write("\n")
        temp_path = f.name

    try:
        pager = os.environ.get("PAGER", "less")
        subprocess.run([pager, temp_path], check=False)
    except FileNotFoundError:
        # Fallback to pydoc.pager if configured pager is missing
        import pydoc

        pydoc.pager(report)
    finally:
        try:
            os.unlink(temp_path)
        except Exception:
            pass
