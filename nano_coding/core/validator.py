import os
from pathlib import Path


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
    blocking = []
    warnings = []

    agents_md = root / "AGENTS.md"
    if not agents_md.exists():
        blocking.append("AGENTS.md not found in project root.")
    else:
        content = agents_md.read_text(encoding="utf-8")
        if "## 基础原则" not in content:
            blocking.append('AGENTS.md is missing the required "## 基础原则" section.')

    if check_forbidden_dirs:
        forbidden_dirs = ["templates", "scripts", "knowledge"]
        for d in forbidden_dirs:
            if (root / d).is_dir():
                blocking.append(
                    f'Forbidden directory at root: {d}/ (violates "生成项目的禁止规则")'
                )

    pre_commit = root / ".git" / "hooks" / "pre-commit"
    if not pre_commit.exists():
        warnings.append(
            "Git pre-commit hook is not installed (.git/hooks/pre-commit missing)."
        )
    elif not os.access(pre_commit, os.X_OK):
        warnings.append("Git pre-commit hook exists but is not executable.")

    for temp_doc in ["TODO.md", "PROGRESS.md"]:
        if (root / temp_doc).exists():
            warnings.append(
                f"{temp_doc} found at project root. Consider removing it after task completion."
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
        warnings.append("No tests directory or test files detected.")

    for path in root.rglob("*"):
        if not path.is_file():
            continue
        try:
            relative = path.relative_to(root)
        except ValueError:
            continue

        if any(part in EXCLUDE_DIRS for part in relative.parts):
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
                f"File exceeds {max_lines} lines ({line_count}): {relative}"
            )

    if check_agents_abort:
        agents_abort = root / "AGENTS_ABORT.md"
        banned_behaviors = root / "BANNED-AGENT-BEHAVIORS.md"

        if not agents_abort.exists() and not banned_behaviors.exists():
            blocking.append("AGENTS_ABORT.md (or BANNED-AGENT-BEHAVIORS.md) not found.")
        else:
            existing_file = agents_abort if agents_abort.exists() else banned_behaviors
            content = existing_file.read_text(encoding="utf-8").strip()
            if not content:
                blocking.append(f"{existing_file.name} is empty.")

    if check_background:
        background_md = root / "BACKGROUND.md"
        if not background_md.exists():
            blocking.append("BACKGROUND.md not found in project root.")

    if check_test_separation:
        unit_dir = root / "tests" / "unit"
        integration_dir = root / "tests" / "integration"

        if not unit_dir.is_dir():
            blocking.append(
                "Missing tests/unit/ directory (required for test type separation)."
            )
        if not integration_dir.is_dir():
            blocking.append(
                "Missing tests/integration/ directory (required for test type separation)."
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
                "No specific test commands found in README.md or AGENTS.md. Document commands like 'pytest -v' or 'npm test'."
            )

    success = len(blocking) == 0
    return {"success": success, "blocking": blocking, "warnings": warnings}
