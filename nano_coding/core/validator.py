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


def _get_validate_config(config: dict) -> dict:
    return config.get("validate", {})


def _get_paths_config(config: dict) -> dict:
    return config.get("paths", {})


def _resolve_config_list(config: dict, key: str, fallback: set[str]) -> set[str]:
    value = config.get(key)
    if isinstance(value, list):
        return set(value)
    return set(fallback)


def _resolve_config_value(config: dict, key: str, fallback):
    value = config.get(key)
    if value is not None:
        return value
    return fallback


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

    def __init__(self, forbidden_dirs: list[str] | None = None):
        self.forbidden_dirs = forbidden_dirs or ["templates", "scripts"]

    def run(self, project_root: Path) -> list[Issue]:
        issues = []
        for d in self.forbidden_dirs:
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

    def __init__(self, temp_docs: list[str] | None = None):
        self.temp_docs = temp_docs or ["TODO.md", "PROGRESS.md"]

    def run(self, project_root: Path) -> list[Issue]:
        issues = []
        for temp_doc in self.temp_docs:
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

    def __init__(self, test_indicators: list[str] | None = None):
        self.test_indicators = test_indicators or ["tests", "test", "spec"]

    def run(self, project_root: Path) -> list[Issue]:
        for indicator in self.test_indicators:
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

    def __init__(
        self,
        agents_abort_file: str = "AGENTS_ABORT.md",
        banned_behaviors_file: str = "BANNED-AGENT-BEHAVIORS.md",
    ):
        self.agents_abort_file = agents_abort_file
        self.banned_behaviors_file = banned_behaviors_file

    def run(self, project_root: Path) -> list[Issue]:
        agents_abort = project_root / self.agents_abort_file
        banned_behaviors = project_root / self.banned_behaviors_file

        if not agents_abort.exists() and not banned_behaviors.exists():
            return [
                Issue(
                    path=None,
                    line=None,
                    rule_id="AGENTS_ABORT_MISSING",
                    message=f"{self.agents_abort_file} (or {self.banned_behaviors_file}) not found.",
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

    def __init__(self, test_separation_dirs: list[str] | None = None):
        self.test_separation_dirs = test_separation_dirs or [
            "tests/unit",
            "tests/integration",
        ]

    def run(self, project_root: Path) -> list[Issue]:
        issues = []
        for dir_path in self.test_separation_dirs:
            if not (project_root / dir_path).is_dir():
                issues.append(
                    Issue(
                        path=None,
                        line=None,
                        rule_id=f"MISSING_{dir_path.replace('/', '_').upper()}_DIR",
                        message=f"Missing {dir_path}/ directory (required for test type separation).",
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

    DEFAULT_PATTERNS = [
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

    def __init__(self, test_command_patterns: list[str] | None = None):
        self.test_command_patterns = test_command_patterns or list(
            self.DEFAULT_PATTERNS
        )

    def run(self, project_root: Path) -> list[Issue]:
        readme = project_root / "README.md"
        agents = project_root / "AGENTS.md"

        combined_content = ""
        if readme.exists():
            combined_content += readme.read_text(encoding="utf-8")
        if agents.exists():
            combined_content += agents.read_text(encoding="utf-8")

        for pattern in self.test_command_patterns:
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


def _count_source_files(
    project_root: Path,
    exclude_dirs: set[str] | None = None,
    file_extensions: set[str] | None = None,
    lock_files: set[str] | None = None,
    test_dirs: set[str] | None = None,
) -> int:
    exclude_dirs = exclude_dirs or EXCLUDE_DIRS
    file_extensions = file_extensions or FILE_EXTENSIONS
    lock_files = lock_files or LOCK_FILES
    test_dirs = test_dirs or {"tests", "test", "spec"}
    count = 0
    for path in project_root.rglob("*"):
        if not path.is_file():
            continue
        try:
            relative = path.relative_to(project_root)
        except ValueError:
            continue
        if any(part in exclude_dirs or part in test_dirs for part in relative.parts):
            continue
        if path.suffix not in file_extensions:
            continue
        if path.name in lock_files:
            continue
        count += 1
    return count


class CheckSubdirAgents(Check):
    name = "subdir_agents"
    principle = "progressive_disclosure"
    practice = "目录分权"
    severity = "warning"
    requires_llm = False

    def __init__(
        self,
        source_file_threshold: int = 50,
        agents_line_threshold: int = 500,
        exclude_dirs: set[str] | None = None,
        file_extensions: set[str] | None = None,
        lock_files: set[str] | None = None,
        test_dirs: set[str] | None = None,
    ):
        self.source_file_threshold = source_file_threshold
        self.agents_line_threshold = agents_line_threshold
        self.exclude_dirs = exclude_dirs
        self.file_extensions = file_extensions
        self.lock_files = lock_files
        self.test_dirs = test_dirs

    def run(self, project_root: Path) -> list[Issue]:
        agents_md = project_root / "AGENTS.md"
        agents_lines = 0
        if agents_md.exists():
            with agents_md.open("rb") as f:
                agents_lines = sum(1 for _ in f)
        if (
            _count_source_files(
                project_root,
                exclude_dirs=self.exclude_dirs,
                file_extensions=self.file_extensions,
                lock_files=self.lock_files,
                test_dirs=self.test_dirs,
            )
            > self.source_file_threshold
            or agents_lines > self.agents_line_threshold
        ):
            if not _has_subdir_agents(project_root):
                return [
                    Issue(
                        path=None,
                        line=None,
                        rule_id="SUBDIR_AGENTS_MISSING",
                        message=f"Project is large (>{self.source_file_threshold} source files or AGENTS.md >{self.agents_line_threshold} lines) but no sub-directory AGENTS.md found.",
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

    def __init__(self, index_files: list[str] | None = None):
        self.index_files = index_files or [".INDEX.md", ".SUMMARY.md"]

    def run(self, project_root: Path) -> list[Issue]:
        if any((project_root / f).exists() for f in self.index_files):
            return []
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


class CheckKnowledgeDir(Check):
    name = "knowledge_dir"
    principle = "progressive_disclosure"
    practice = "AGENTS可读"
    severity = "warning"
    requires_llm = False

    def __init__(self, knowledge_dir: str | None = None):
        self.knowledge_dir = knowledge_dir or "knowledge"

    def run(self, project_root: Path) -> list[Issue]:
        if not (project_root / self.knowledge_dir).is_dir():
            return [
                Issue(
                    path=None,
                    line=None,
                    rule_id="KNOWLEDGE_DIR_MISSING",
                    message=f"{self.knowledge_dir}/ directory not found in project root. Consider creating one for accumulated learnings.",
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

    def __init__(self, max_lines: int = 500, max_blocks: int = 20):
        self.max_lines = max_lines
        self.max_blocks = max_blocks

    def run(self, project_root: Path) -> list[Issue]:
        agents_md = project_root / "AGENTS.md"
        if not agents_md.exists():
            return []
        content = agents_md.read_text(encoding="utf-8")
        lines = content.splitlines()
        blocks = extractPrincipleBlocks(content)
        if len(lines) > self.max_lines or len(blocks) > self.max_blocks:
            if not _has_subdir_agents(project_root):
                return [
                    Issue(
                        path=None,
                        line=None,
                        rule_id="SUBDIR_AGENTS_OVERFLOW",
                        message=f"AGENTS.md is large (>{self.max_lines} lines or >{self.max_blocks} principle sections) but no sub-directory AGENTS.md found for overflow.",
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

    def __init__(self, mixed_ratio: float = 0.30):
        self.mixed_ratio = mixed_ratio

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
        if non_trivial > 0 and mixed / non_trivial > self.mixed_ratio:
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

    def __init__(self, background_keywords: list[str] | None = None):
        self.background_keywords = background_keywords or [
            "愿景",
            "约束",
            "业务逻辑",
            "避坑",
        ]

    def run(self, project_root: Path) -> list[Issue]:
        bg = project_root / "BACKGROUND.md"
        if not bg.exists():
            return []
        content = bg.read_text(encoding="utf-8")
        missing = [kw for kw in self.background_keywords if kw not in content]
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

    DEFAULT_SENSITIVE_PREFIXES = (".env", "credentials", "secret")
    DEFAULT_SENSITIVE_SUFFIXES = (".key", ".pem", ".p12", ".log")
    DEFAULT_EXACT_NAMES = ("id_rsa",)

    def __init__(
        self,
        log_size_bytes: int = 1048576,
        sensitive_prefixes: tuple[str, ...] | None = None,
        sensitive_suffixes: tuple[str, ...] | None = None,
        exact_names: tuple[str, ...] | None = None,
    ):
        self.log_size_bytes = log_size_bytes
        self.sensitive_prefixes = sensitive_prefixes or self.DEFAULT_SENSITIVE_PREFIXES
        self.sensitive_suffixes = sensitive_suffixes or self.DEFAULT_SENSITIVE_SUFFIXES
        self.exact_names = exact_names or self.DEFAULT_EXACT_NAMES

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
            if name in self.exact_names:
                is_sensitive = True
            if not is_sensitive and any(
                name.startswith(p) or name.startswith("." + p)
                for p in self.sensitive_prefixes
            ):
                is_sensitive = True
            if not is_sensitive and any(
                name.endswith(suf) for suf in self.sensitive_suffixes
            ):
                if name.endswith(".log") and path.is_file():
                    try:
                        if path.stat().st_size > self.log_size_bytes:
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


class ProtectedDocsCheck(Check):
    name = "protected_docs"
    principle = "core_principles"
    practice = "变更确认"
    severity = "warning"
    requires_llm = False

    DEFAULT_PROTECTED_DOCUMENTS = [
        "AGENTS.md",
        "README.md",
        "AGENTS_ABORT.md",
        "BANNED-AGENT-BEHAVIORS.md",
        "principles/core.md",
        ".nano-coding-agent/principles/core.md",
        ".nano-coding-agent/config.yaml",
    ]

    def run(self, project_root: Path) -> list[Issue]:
        config = config_loader.resolve_config(project_root)
        protected = config.get("protected_documents", self.DEFAULT_PROTECTED_DOCUMENTS)
        try:
            proc = subprocess.run(
                ["git", "diff", "--cached", "--name-only"],
                cwd=str(project_root),
                capture_output=True,
                text=True,
                check=False,
            )
        except Exception:
            return []
        if proc.returncode != 0:
            return []
        staged_files = [
            line.strip() for line in proc.stdout.splitlines() if line.strip()
        ]
        affected = [f for f in staged_files if f in protected]
        if affected:
            return [
                Issue(
                    path=None,
                    line=None,
                    rule_id="PROTECTED_DOCS_STAGED",
                    message=f"Staged changes affect protected documents: {', '.join(affected)}. Please review carefully.",
                    principle=self.principle,
                    practice=self.practice,
                    severity=self.severity,
                )
            ]
        return []


class CheckCommitSize(Check):
    name = "commit_size"
    principle = "git_commit"
    practice = "提交粒度"
    severity = "warning"
    requires_llm = False

    def __init__(self, max_files: int = 10, max_insertions: int = 500):
        self.max_files = max_files
        self.max_insertions = max_insertions

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
        if files_changed > self.max_files or insertions > self.max_insertions:
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

    DEFAULT_LOCK_MANAGER_MAP = {
        "package-lock.json": "npm",
        "pnpm-lock.yaml": "pnpm",
        "yarn.lock": "yarn",
        "Cargo.lock": "cargo",
        "poetry.lock": "poetry",
        "Pipfile.lock": "pipenv",
    }

    DEFAULT_BAD_PATTERNS = {
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

    def __init__(
        self,
        lock_manager_map: dict[str, str] | None = None,
        bad_patterns: dict[str, list[str]] | None = None,
    ):
        self.lock_manager_map = lock_manager_map or dict(self.DEFAULT_LOCK_MANAGER_MAP)
        self.bad_patterns = bad_patterns or {
            k: list(v) for k, v in self.DEFAULT_BAD_PATTERNS.items()
        }

    def run(self, project_root: Path) -> list[Issue]:
        detected: list[str] = []
        for lock_file, manager in self.lock_manager_map.items():
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
            for pattern in self.bad_patterns.get(manager, []):
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

    def __init__(
        self,
        max_lines: int = 1000,
        max_principle_chars: int = 1000,
        max_practice_chars: int = 150,
    ):
        self.max_lines = max_lines
        self.max_principle_chars = max_principle_chars
        self.max_practice_chars = max_practice_chars

    def run(self, project_root: Path) -> list[Issue]:
        agents_md = project_root / "AGENTS.md"
        if not agents_md.exists():
            return []
        issues: list[Issue] = []
        lines = agents_md.read_text(encoding="utf-8").splitlines()
        if len(lines) > self.max_lines:
            issues.append(
                Issue(
                    path="AGENTS.md",
                    line=None,
                    rule_id="AGENTS_FILE_TOO_LONG",
                    message=f"AGENTS.md exceeds {self.max_lines} lines ({len(lines)}).",
                    principle=self.principle,
                    practice=self.practice,
                    severity=self.severity,
                )
            )
        blocks = extractPrincipleBlocks(agents_md.read_text(encoding="utf-8"))
        for block in blocks:
            total_chars = len(block.title) + len(block.body)
            if total_chars > self.max_principle_chars:
                issues.append(
                    Issue(
                        path="AGENTS.md",
                        line=None,
                        rule_id="PRINCIPLE_BLOCK_TOO_LONG",
                        message=f'Principle block "{block.title}" exceeds {self.max_principle_chars} chars ({total_chars}).',
                        principle=self.principle,
                        practice=self.practice,
                        severity=self.severity,
                    )
                )
            for line in block.body.splitlines():
                if line.strip().startswith("- "):
                    if len(line) > self.max_practice_chars:
                        issues.append(
                            Issue(
                                path="AGENTS.md",
                                line=None,
                                rule_id="PRACTICE_LINE_TOO_LONG",
                                message=f"Practice line exceeds {self.max_practice_chars} chars: {line[:80]}...",
                                principle=self.principle,
                                practice=self.practice,
                                severity=self.severity,
                            )
                        )
        return issues


def build_validation_engine(
    max_lines: int = 1000,
    exclude_dirs: set[str] | None = None,
    config: dict | None = None,
) -> CheckEngine:
    config = config or {}
    validate_cfg = _get_validate_config(config)
    paths_cfg = _get_paths_config(config)
    checks_config = config.get("checks", {})

    file_length_cfg = checks_config.get("file_length", {})
    file_length_max_lines = file_length_cfg.get("max_lines", max_lines)

    subdir_agents_cfg = checks_config.get("subdir_agents", {})
    overflow_cfg = checks_config.get("subdir_agents_overflow", {})
    agents_language_cfg = checks_config.get("agents_language", {})
    commit_size_cfg = checks_config.get("commit_size", {})
    agents_length_cfg = checks_config.get("agents_length", {})
    gitignore_tempfiles_cfg = checks_config.get("gitignore_tempfiles", {})

    temp_docs = validate_cfg.get("temp_docs")
    test_indicators = validate_cfg.get("test_indicators")
    agents_abort_file = paths_cfg.get("agents_abort", "AGENTS_ABORT.md")
    banned_behaviors_file = paths_cfg.get(
        "banned_behaviors", "BANNED-AGENT-BEHAVIORS.md"
    )
    test_separation_dirs = validate_cfg.get("test_separation_dirs")
    test_command_patterns = validate_cfg.get("test_command_patterns")
    index_files = paths_cfg.get("index_files")
    knowledge_dir = paths_cfg.get("knowledge_dir")
    background_keywords = validate_cfg.get("background_keywords")
    sensitive_file_rules = validate_cfg.get("sensitive_file_rules", {})
    package_manager_cfg = validate_cfg.get("package_manager", {})

    file_extensions = _resolve_config_list(
        validate_cfg, "file_extensions", FILE_EXTENSIONS
    )
    lock_files = _resolve_config_list(validate_cfg, "lock_files", LOCK_FILES)
    test_dirs = _resolve_config_list(paths_cfg, "test_dirs", {"tests", "test", "spec"})

    engine = CheckEngine()
    engine.register(AgentsMdExistsCheck())
    engine.register(AgentsMdHasSectionCheck())
    engine.register(PreCommitHookCheck())
    engine.register(TempDocsCheck(temp_docs=temp_docs))
    engine.register(TestsExistCheck(test_indicators=test_indicators))
    engine.register(
        FileLengthCheck(max_lines=file_length_max_lines, exclude_dirs=exclude_dirs)
    )
    engine.register(
        AgentsAbortCheck(
            agents_abort_file=agents_abort_file,
            banned_behaviors_file=banned_behaviors_file,
        )
    )
    engine.register(BackgroundMdCheck())
    engine.register(TestSeparationCheck(test_separation_dirs=test_separation_dirs))
    engine.register(TestCommandsCheck(test_command_patterns=test_command_patterns))
    engine.register(ProtectedDocsCheck())
    engine.register(
        CheckSubdirAgents(
            source_file_threshold=subdir_agents_cfg.get("source_file_threshold", 50),
            agents_line_threshold=subdir_agents_cfg.get("agents_line_threshold", 500),
            exclude_dirs=exclude_dirs if exclude_dirs else EXCLUDE_DIRS,
            file_extensions=file_extensions,
            lock_files=lock_files,
            test_dirs=test_dirs,
        )
    )
    engine.register(CheckIndexSummary(index_files=index_files))
    engine.register(CheckKnowledgeDir(knowledge_dir=knowledge_dir))
    engine.register(CheckKnowledgeDirExperience(knowledge_dir=knowledge_dir))
    engine.register(
        CheckSubdirAgentsOverflow(
            max_lines=overflow_cfg.get("max_lines", 500),
            max_blocks=overflow_cfg.get("max_blocks", 20),
        )
    )
    engine.register(
        CheckAgentsLanguage(
            mixed_ratio=agents_language_cfg.get("mixed_ratio", 0.30),
        )
    )
    engine.register(CheckReadmeI18n())
    engine.register(CheckBackgroundContent(background_keywords=background_keywords))
    engine.register(
        CheckGitignoreTempfiles(
            log_size_bytes=gitignore_tempfiles_cfg.get(
                "log_size_bytes", sensitive_file_rules.get("log_size_bytes", 1048576)
            ),
            sensitive_prefixes=tuple(
                sensitive_file_rules.get(
                    "prefixes", CheckGitignoreTempfiles.DEFAULT_SENSITIVE_PREFIXES
                )
            ),
            sensitive_suffixes=tuple(
                sensitive_file_rules.get(
                    "suffixes", CheckGitignoreTempfiles.DEFAULT_SENSITIVE_SUFFIXES
                )
            ),
            exact_names=tuple(
                sensitive_file_rules.get(
                    "exact_names", CheckGitignoreTempfiles.DEFAULT_EXACT_NAMES
                )
            ),
        )
    )
    engine.register(
        CheckCommitSize(
            max_files=commit_size_cfg.get("max_files", 10),
            max_insertions=commit_size_cfg.get("max_insertions", 500),
        )
    )
    engine.register(
        CheckPackageManager(
            lock_manager_map=package_manager_cfg.get("lock_manager_map"),
            bad_patterns=package_manager_cfg.get("bad_patterns"),
        )
    )
    engine.register(
        CheckAgentsLength(
            max_lines=agents_length_cfg.get("max_lines", 1000),
            max_principle_chars=agents_length_cfg.get("max_principle_chars", 1000),
            max_practice_chars=agents_length_cfg.get("max_practice_chars", 150),
        )
    )
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
    validate_config = _get_validate_config(config)

    if isinstance(validate_config.get("max_lines"), int):
        max_lines = validate_config["max_lines"]

    rules = list(DEFAULT_RULES)
    if isinstance(validate_config.get("rules"), list):
        rules.extend(validate_config["rules"])

    exclude_dirs = set(EXCLUDE_DIRS)
    if isinstance(validate_config.get("ignore_dirs"), list):
        exclude_dirs.update(validate_config["ignore_dirs"])

    engine = build_validation_engine(
        max_lines=max_lines, exclude_dirs=exclude_dirs, config=config
    )

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
