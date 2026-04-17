import os
import subprocess
import sys
from pathlib import Path

import click

from nano_coding.core import config_loader
from nano_coding.core.installer import install_agent
from nano_coding.core.principles import (
    extractPrincipleBlocks,
    mergePrinciplesIntoDocument,
    resolve_principle_tags,
)
from nano_coding.core.scanner import (
    get_staged_files,
    run_audit_scan,
    run_security_scan,
)
from nano_coding.core.registry import register_practice
from nano_coding.core.validator import (
    DEFAULT_RULES,
    EXCLUDE_DIRS,
    FILE_EXTENSIONS,
    build_validation_engine,
    format_validation_report,
    issue_to_dict,
    show_report_interactively,
)
from nano_coding.core.check_engine import Issue


@click.command()
@click.argument("target_dir")
@click.option(
    "--yes",
    "-y",
    is_flag=True,
    help="Skip interactive prompts and use defaults.",
)
@register_practice(
    principle='行为边界与"防呆"原则 (Guardrails & Boundaries)',
    practices={"禁止操作": ["install"]},
)
def install(target_dir: str, yes: bool) -> None:
    """将pre-commit钩子和基础principles/目录安装到Git仓库中。

    Examples:

        $ uv run nano-coding install .
        $ uv run nano-coding install . --yes
    """
    install_agent(target_dir, interactive=not yes)


@click.command()
@click.argument("target_dir")
@click.option(
    "--check-agents-abort",
    is_flag=True,
    help="Validate AGENTS_ABORT.md or BANNED-AGENT-BEHAVIORS.md exists and is non-empty.",
)
@click.option(
    "--check-background",
    is_flag=True,
    help="Validate BACKGROUND.md exists in project root.",
)
@click.option(
    "--check-test-separation",
    is_flag=True,
    help="Validate tests/unit/ and tests/integration/ directories exist.",
)
@click.option(
    "--check-test-commands",
    is_flag=True,
    help="Validate README.md or AGENTS.md contains specific test commands.",
)
@click.option(
    "--check-subdir-agents",
    is_flag=True,
    help="Warn if large project lacks sub-directory AGENTS.md.",
)
@click.option(
    "--check-index-summary",
    is_flag=True,
    help="Warn if .INDEX.md or .SUMMARY.md is missing.",
)
@click.option(
    "--check-knowledge-dir",
    is_flag=True,
    help="Warn if knowledge/ directory is missing.",
)
@click.option(
    "--check-subdir-agents-overflow",
    is_flag=True,
    help="Warn if AGENTS.md is large but has no overflow sub-directory.",
)
@click.option(
    "--check-agents-language",
    is_flag=True,
    help="Warn if AGENTS.md uses mixed scripts extensively.",
)
@click.option(
    "--check-readme-i18n",
    is_flag=True,
    help="Warn if README.md lacks translated variants or language links.",
)
@click.option(
    "--check-background-content",
    is_flag=True,
    help="Warn if BACKGROUND.md is missing recommended keywords.",
)
@click.option(
    "--check-gitignore-tempfiles",
    is_flag=True,
    help="Warn about untracked sensitive files or missing .gitignore.",
)
@click.option(
    "--check-commit-size",
    is_flag=True,
    help="Warn if staged commit exceeds size limits.",
)
@click.option(
    "--check-package-manager",
    is_flag=True,
    help="Warn if lock file and documented install commands mismatch.",
)
@click.option(
    "--check-agents-length",
    is_flag=True,
    help="Warn if AGENTS.md or principle blocks exceed length limits.",
)
@click.option(
    "--interactive",
    "-i",
    is_flag=True,
    help="Display results in an interactive pager (less-style).",
)
@register_practice(
    principle='行为边界与"防呆"原则 (Guardrails & Boundaries)',
    practices={"禁止操作": ["validate", "validate --check-agents-abort"]},
)
@register_practice(
    principle="项目背景文档 (BACKGROUND.md)",
    practices={"创建 BACKGROUND.md": ["validate", "validate --check-background"]},
)
@register_practice(
    principle="测试先行原则（TDD First）",
    practices={"区分测试类型": ["validate", "validate --check-test-separation"]},
)
@register_practice(
    principle="测试先行原则（TDD First）",
    practices={"具体的工具链": ["validate", "validate --check-test-commands"]},
)
def validate(
    target_dir: str,
    check_agents_abort: bool,
    check_background: bool,
    check_test_separation: bool,
    check_test_commands: bool,
    check_subdir_agents: bool,
    check_index_summary: bool,
    check_knowledge_dir: bool,
    check_subdir_agents_overflow: bool,
    check_agents_language: bool,
    check_readme_i18n: bool,
    check_background_content: bool,
    check_gitignore_tempfiles: bool,
    check_commit_size: bool,
    check_package_manager: bool,
    check_agents_length: bool,
    interactive: bool,
) -> None:
    """验证项目是否满足基础治理规则。

    Examples:

        $ uv run nano-coding validate .
        $ uv run nano-coding validate . --check-agents-abort --check-background
        $ uv run nano-coding validate . --interactive
    """
    root = Path(target_dir).resolve()

    config = config_loader.resolve_config(root)
    validate_config = config.get("validate", {})

    max_lines = 1000
    if isinstance(validate_config.get("max_lines"), int):
        max_lines = validate_config["max_lines"]

    rules = list(DEFAULT_RULES)
    if isinstance(validate_config.get("rules"), list):
        rules.extend(validate_config["rules"])

    exclude_dirs = set(EXCLUDE_DIRS)
    if isinstance(validate_config.get("ignore_dirs"), list):
        exclude_dirs.update(validate_config["ignore_dirs"])

    file_extensions = set(FILE_EXTENSIONS)
    if isinstance(validate_config.get("file_extensions"), list):
        file_extensions = set(validate_config["file_extensions"])

    lock_files = set(validate_config.get("lock_files", []))

    engine = build_validation_engine(
        max_lines=max_lines, exclude_dirs=exclude_dirs, config=config
    )

    any_flag = (
        check_agents_abort
        or check_background
        or check_test_separation
        or check_test_commands
        or check_subdir_agents
        or check_index_summary
        or check_knowledge_dir
        or check_subdir_agents_overflow
        or check_agents_language
        or check_readme_i18n
        or check_background_content
        or check_gitignore_tempfiles
        or check_commit_size
        or check_package_manager
        or check_agents_length
    )
    if any_flag:
        names = []
        if check_agents_abort:
            names.append("agents_abort")
        if check_background:
            names.append("background_md")
        if check_test_separation:
            names.append("test_separation")
        if check_test_commands:
            names.append("test_commands")
        if check_subdir_agents:
            names.append("subdir_agents")
        if check_index_summary:
            names.append("index_summary")
        if check_knowledge_dir:
            names.append("knowledge_dir")
            names.append("knowledge_dir_experience")
        if check_subdir_agents_overflow:
            names.append("subdir_agents_overflow")
        if check_agents_language:
            names.append("agents_language")
        if check_readme_i18n:
            names.append("readme_i18n")
        if check_background_content:
            names.append("background_content")
        if check_gitignore_tempfiles:
            names.append("gitignore_tempfiles")
        if check_commit_size:
            names.append("commit_size")
        if check_package_manager:
            names.append("package_manager")
        if check_agents_length:
            names.append("agents_length")
    else:
        names = None  # run all requires_llm=False checks

    results = engine.run_all(root, names=names, llm=False)

    blocking: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []

    for issues in results.values():
        for issue in issues:
            issue_dict = issue_to_dict(issue)
            if issue.severity == "blocking":
                blocking.append(issue_dict)
            else:
                warnings.append(issue_dict)

    success = len(blocking) == 0
    result = {
        "success": success,
        "blocking": blocking,
        "warnings": warnings,
        "rules": rules,
    }

    report = format_validation_report(result)

    if interactive:
        show_report_interactively(report)
    else:
        click.echo(report)

    sys.exit(0 if result["success"] else 1)


@click.command()
@click.argument("target", default="AGENTS.md", required=False)
@register_practice(
    principle="最重要原则：核心指导原则需要由人类审核",
    practices={"共性个性区分": ["update"]},
)
def update(target: str) -> None:
    """将principles/目录下的原则块合并到AGENTS.md中，通过语义相似度去重。

    Examples:

        $ uv run nano-coding update
        $ uv run nano-coding update .
        $ uv run nano-coding update /path/to/project
    """
    target_path = Path(target)
    if target_path.is_dir():
        target_file = target_path / "AGENTS.md"
    else:
        target_file = target_path

    if not target_file.exists():
        click.echo(f"[ERROR] Target file not found: {target_file}")
        sys.exit(1)

    agent_principles_dir = target_file.parent / ".nano-coding-agent" / "principles"
    legacy_principles_dir = target_file.parent / "principles"

    if agent_principles_dir.exists() and agent_principles_dir.is_dir():
        principles_dir = agent_principles_dir
    elif legacy_principles_dir.exists() and legacy_principles_dir.is_dir():
        principles_dir = legacy_principles_dir
    else:
        click.echo(
            f"[ERROR] Principles directory not found: tried {agent_principles_dir} "
            f"and {legacy_principles_dir}"
        )
        sys.exit(1)

    md_files = sorted(principles_dir.glob("*.md"))
    if not md_files:
        click.echo(f"[ERROR] No markdown files found in {principles_dir}")
        sys.exit(1)

    target_content = target_file.read_text(encoding="utf-8")
    all_blocks: list = []
    for md_file in md_files:
        content = md_file.read_text(encoding="utf-8")
        blocks = extractPrincipleBlocks(content)
        all_blocks.extend(blocks)

    target_dir = target_file.parent
    all_blocks = resolve_principle_tags(
        all_blocks,
        str(target_dir) if target_dir.exists() else None,
    )

    config = config_loader.resolve_config(target_dir)
    semantic_threshold = config.get("semantic_threshold", 0.88)
    result = mergePrinciplesIntoDocument(
        target_content, all_blocks, semantic_threshold=semantic_threshold
    )

    for warning in result.warnings:
        click.echo(warning, err=True)

    target_file.write_text(result.merged_doc, encoding="utf-8")
    click.echo(f"Merged {len(all_blocks)} principle blocks into {target_file}")


def _discover_source_files(
    root: Path,
    exclude_dirs: set[str] | None = None,
    file_extensions: set[str] | None = None,
) -> list[str]:
    exclude_dirs = exclude_dirs or EXCLUDE_DIRS
    file_extensions = file_extensions or FILE_EXTENSIONS

    if (root / ".git").is_dir():
        try:
            result = subprocess.run(
                [
                    "git",
                    "-C",
                    str(root),
                    "ls-files",
                    "--cached",
                    "--others",
                    "--exclude-standard",
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode == 0:
                files: list[str] = []
                for line in result.stdout.strip().split("\n"):
                    line = line.strip()
                    if not line:
                        continue
                    path = root / line
                    if not path.is_file():
                        continue
                    relative = Path(line)
                    if any(part in exclude_dirs for part in relative.parts):
                        continue
                    if relative.suffix not in file_extensions:
                        continue
                    files.append(str(relative))
                return files
        except Exception:
            pass

    files: list[str] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        try:
            relative = path.relative_to(root)
        except ValueError:
            continue
        if any(part in exclude_dirs for part in relative.parts):
            continue
        if path.suffix not in file_extensions:
            continue
        files.append(str(relative))
    return files


def _format_check_issue(issue: Issue) -> str:
    if issue.path:
        loc = f"{issue.path}:{issue.line}" if issue.line is not None else issue.path
        return f"[{issue.rule_id}] {loc}: {issue.message}"
    return f"[{issue.rule_id}] {issue.message}"


def _build_unified_report(
    blocking: list[str],
    warnings: list[str],
    suggestions: list[str],
) -> str:
    lines: list[str] = []
    lines.append("SUMMARY")
    lines.append("=======")
    lines.append(
        f"Blocking: {len(blocking)} | Warnings: {len(warnings)} | Suggestions: {len(suggestions)}"
    )
    lines.append("")

    if blocking:
        lines.append("BLOCKING")
        lines.append("========")
        for item in blocking:
            lines.append(item)
        lines.append("")

    if warnings:
        lines.append("WARNINGS")
        lines.append("========")
        for item in warnings:
            lines.append(item)
        lines.append("")

    if suggestions:
        lines.append("SUGGESTIONS")
        lines.append("===========")
        for item in suggestions:
            lines.append(item)
        lines.append("")

    return "\n".join(lines)


@click.command()
@click.option(
    "--path", default=".", help="Directory to scan (default: current directory)"
)
@click.option("--level", default="standard", help="Audit level (default: standard)")
@click.option(
    "--interactive",
    "-i",
    is_flag=True,
    help="Display results in an interactive pager (less-style).",
)
@click.option(
    "--staged",
    is_flag=True,
    help="Limit scan to staged files only.",
)
@register_practice(
    principle='行为边界与"防呆"原则 (Guardrails & Boundaries)',
    practices={"安全防线": ["scan"]},
)
def scan(path: str, level: str, interactive: bool, staged: bool) -> None:
    """对项目运行安全和审计扫描。报告阻塞性问题、警告和建议。

    Examples:

        $ uv run nano-coding scan --path .
        $ uv run nano-coding scan --path . --interactive
        $ uv run nano-coding scan --path . --staged
    """
    root = Path(path).resolve()
    original_dir = os.getcwd()
    if path != ".":
        os.chdir(root)

    try:
        config = config_loader.resolve_config(root)
        validate_cfg = config.get("validate", {})
        scan_exclude_dirs = set(EXCLUDE_DIRS)
        if isinstance(validate_cfg.get("ignore_dirs"), list):
            scan_exclude_dirs.update(validate_cfg["ignore_dirs"])
        engine = build_validation_engine(exclude_dirs=scan_exclude_dirs, config=config)
        check_results = engine.run_all(root, llm=False)

        blocking: list[str] = []
        warnings: list[str] = []

        for issues in check_results.values():
            for issue in issues:
                formatted = _format_check_issue(issue)
                if issue.severity == "blocking":
                    blocking.append(formatted)
                else:
                    warnings.append(formatted)

        security = run_security_scan()
        blocking.extend(security.get("blocking", []))
        warnings.extend(security.get("warnings", []))
        suggestions: list[str] = list(security.get("suggestions", []))

        validate_cfg = config.get("validate", {})
        scan_exclude_dirs = set(EXCLUDE_DIRS)
        if isinstance(validate_cfg.get("ignore_dirs"), list):
            scan_exclude_dirs.update(validate_cfg["ignore_dirs"])
        scan_file_extensions = set(FILE_EXTENSIONS)
        if isinstance(validate_cfg.get("file_extensions"), list):
            scan_file_extensions = set(validate_cfg["file_extensions"])

        if staged:
            audit_files = get_staged_files()
        else:
            audit_files = _discover_source_files(
                root,
                exclude_dirs=scan_exclude_dirs,
                file_extensions=scan_file_extensions,
            )
        audit = run_audit_scan(files=audit_files, level=level)
        blocking.extend(audit.get("blocking", []))
        warnings.extend(audit.get("warnings", []))
        suggestions.extend(audit.get("suggestions", []))

        report = _build_unified_report(blocking, warnings, suggestions)

        if interactive:
            show_report_interactively(report)
        else:
            click.echo(report)

        sys.exit(1 if blocking else 0)
    finally:
        os.chdir(original_dir)


@click.command(name="confirm-principles")
@click.option("--path", default=".", help="Project path (default: current directory)")
@click.option(
    "--yes", "-y", is_flag=True, help="Skip interactive prompt and auto-confirm."
)
def confirm_principles(path: str, yes: bool) -> None:
    """Check if staged changes affect protected documents and prompt for confirmation.

    Examples:

        $ uv run nano-coding confirm-principles --path .
        $ uv run nano-coding confirm-principles --path . --yes
    """
    root = Path(path).resolve()
    config = config_loader.resolve_config(root)
    protected = config.get(
        "protected_documents",
        [
            "AGENTS.md",
            "AGENTS_ABORT.md",
            "BANNED-AGENT-BEHAVIORS.md",
            ".nano-coding-agent/config.yaml",
        ],
    )

    try:
        proc = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            cwd=str(root),
            capture_output=True,
            text=True,
            check=False,
        )
    except Exception:
        sys.exit(0)

    if proc.returncode != 0:
        sys.exit(0)

    staged_files = [line.strip() for line in proc.stdout.splitlines() if line.strip()]
    affected = [f for f in staged_files if f in protected]

    if not affected:
        sys.exit(0)

    files_str = ", ".join(affected)

    if yes:
        click.echo(f"Changes to protected documents confirmed via --yes: {files_str}")
        sys.exit(0)

    answer = click.prompt(
        f"You are about to commit changes to protected documents: {files_str}. Have you personally reviewed these changes? (yes/no)",
        type=str,
    )
    if answer.strip().lower() != "yes":
        click.echo(
            "Aborting commit: protected document changes not confirmed.", err=True
        )
        sys.exit(1)

    sys.exit(0)


commands = [install, validate, update, scan, confirm_principles]
