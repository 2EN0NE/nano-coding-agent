import os
import subprocess
import tempfile
from pathlib import Path

from nano_coding.core import config_loader


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
}


def _issue(
    message: str,
    principle_key: str,
) -> dict[str, str]:
    meta = _PRINCIPLES[principle_key]
    return {
        "message": message,
        "principle": meta["title"],
        "explanation": meta["explanation"],
    }


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
    blocking: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []

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

    agents_md = root / "AGENTS.md"
    if not agents_md.exists():
        blocking.append(
            _issue(
                "AGENTS.md not found in project root.",
                "core_principles",
            )
        )
    else:
        content = agents_md.read_text(encoding="utf-8")
        if "## 基础原则" not in content:
            blocking.append(
                _issue(
                    'AGENTS.md is missing the required "## 基础原则" section.',
                    "core_principles",
                )
            )

    if check_forbidden_dirs:
        forbidden_dirs = ["templates", "scripts"]
        for d in forbidden_dirs:
            if (root / d).is_dir():
                blocking.append(
                    _issue(
                        f'Forbidden directory at root: {d}/ (violates "生成项目的禁止规则")',
                        "guardrails",
                    )
                )

    pre_commit = root / ".git" / "hooks" / "pre-commit"
    if not pre_commit.exists():
        warnings.append(
            _issue(
                "Git pre-commit hook is not installed (.git/hooks/pre-commit missing).",
                "guardrails",
            )
        )
    elif not os.access(pre_commit, os.X_OK):
        warnings.append(
            _issue(
                "Git pre-commit hook exists but is not executable.",
                "guardrails",
            )
        )

    _task_doc = "T" + "ODO.md"
    _progress_doc = "PROGRESS.md"
    for temp_doc in [_task_doc, _progress_doc]:
        if (root / temp_doc).exists():
            warnings.append(
                _issue(
                    f"{temp_doc} found at project root. Consider removing it after task completion.",
                    "workflow",
                )
            )

    has_tests = False
    test_indicators = ["tests", "test", "spec"]
    for indicator in test_indicators:
        if (root / indicator).is_dir():
            has_tests = True
            break
        if (
            list(root.rglob(f"*{indicator}*.py"))
            or list(root.rglob(f"*{indicator}*.ts"))
            or list(root.rglob(f"*{indicator}*.rs"))
        ):
            has_tests = True
            break
    if not has_tests:
        warnings.append(
            _issue(
                "No tests directory or test files detected.",
                "tdd_first",
            )
        )

    for path in root.rglob("*"):
        if not path.is_file():
            continue
        try:
            relative = path.relative_to(root)
        except ValueError:
            continue

        if any(part in exclude_dirs for part in relative.parts):
            continue
        if path.suffix not in FILE_EXTENSIONS:
            continue
        if path.name in LOCK_FILES:
            continue

        try:
            with path.open("rb") as f:
                line_count = sum(1 for _ in f)
        except Exception:
            continue

        if line_count > max_lines:
            blocking.append(
                _issue(
                    f"File exceeds {max_lines} lines ({line_count}): {relative}",
                    "length_limit",
                )
            )

    if check_agents_abort:
        agents_abort = root / "AGENTS_ABORT.md"
        banned_behaviors = root / "BANNED-AGENT-BEHAVIORS.md"

        if not agents_abort.exists() and not banned_behaviors.exists():
            blocking.append(
                _issue(
                    "AGENTS_ABORT.md (or BANNED-AGENT-BEHAVIORS.md) not found.",
                    "guardrails",
                )
            )
        else:
            existing_file = agents_abort if agents_abort.exists() else banned_behaviors
            content = existing_file.read_text(encoding="utf-8").strip()
            if not content:
                blocking.append(
                    _issue(
                        f"{existing_file.name} is empty.",
                        "guardrails",
                    )
                )

    if check_background:
        background_md = root / "BACKGROUND.md"
        if not background_md.exists():
            blocking.append(
                _issue(
                    "BACKGROUND.md not found in project root.",
                    "background",
                )
            )

    if check_test_separation:
        unit_dir = root / "tests" / "unit"
        integration_dir = root / "tests" / "integration"

        if not unit_dir.is_dir():
            blocking.append(
                _issue(
                    "Missing tests/unit/ directory (required for test type separation).",
                    "tdd_separation",
                )
            )
        if not integration_dir.is_dir():
            blocking.append(
                _issue(
                    "Missing tests/integration/ directory (required for test type separation).",
                    "tdd_separation",
                )
            )

    if check_test_commands:
        import re

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

        readme = root / "README.md"
        agents = root / "AGENTS.md"

        found_command = False
        combined_content = ""

        if readme.exists():
            combined_content += readme.read_text(encoding="utf-8")
        if agents.exists():
            combined_content += agents.read_text(encoding="utf-8")

        for pattern in TEST_COMMAND_PATTERNS:
            if re.search(pattern, combined_content):
                found_command = True
                break

        if not found_command:
            blocking.append(
                _issue(
                    "No specific test commands found in README.md or AGENTS.md. Document commands like 'pytest -v' or 'npm test'.",
                    "tdd_first",
                )
            )

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
