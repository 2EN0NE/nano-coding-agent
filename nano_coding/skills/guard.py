import os
import sys
from pathlib import Path

import click

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
    format_validation_report,
    show_report_interactively,
    validate_project,
)


@click.command()
@click.argument("target_dir")
@register_practice(
    principle='行为边界与"防呆"原则 (Guardrails & Boundaries)',
    practices={"禁止操作": ["install"]},
)
def install(target_dir: str) -> None:
    """将pre-commit钩子和基础principles/目录安装到Git仓库中。

    Examples:

        $ uv run nano-coding install .
    """
    install_agent(target_dir)


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
    interactive: bool,
) -> None:
    """验证项目是否满足基础治理规则。

    Examples:

        $ uv run nano-coding validate .
        $ uv run nano-coding validate . --check-agents-abort --check-background
        $ uv run nano-coding validate . --interactive
    """
    result = validate_project(
        target_dir,
        check_agents_abort=check_agents_abort,
        check_background=check_background,
        check_test_separation=check_test_separation,
        check_test_commands=check_test_commands,
    )

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
    merged = mergePrinciplesIntoDocument(target_content, all_blocks)

    target_file.write_text(merged, encoding="utf-8")
    click.echo(f"Merged {len(all_blocks)} principle blocks into {target_file}")


@click.command()
@click.option(
    "--path", default=".", help="Directory to scan (default: current directory)"
)
@click.option("--level", default="standard", help="Audit level (default: standard)")
@register_practice(
    principle='行为边界与"防呆"原则 (Guardrails & Boundaries)',
    practices={"安全防线": ["scan"]},
)
def scan(path: str, level: str) -> None:
    """对项目运行安全和审计扫描。报告阻塞性问题、警告和建议。

    Examples:

        $ uv run nano-coding scan --path .
    """
    original_dir = os.getcwd()
    if path != ".":
        os.chdir(path)

    try:
        security = run_security_scan()
        audit = run_audit_scan(files=get_staged_files(), level=level)

        for issue in security.get("blocking", []):
            click.echo(f"[SECURITY BLOCKING] {issue}")
        for issue in security.get("warnings", []):
            click.echo(f"[SECURITY WARNING] {issue}")
        for issue in security.get("suggestions", []):
            click.echo(f"[SECURITY SUGGESTION] {issue}")

        for issue in audit.get("blocking", []):
            click.echo(f"[AUDIT BLOCKING] {issue}")
        for issue in audit.get("warnings", []):
            click.echo(f"[AUDIT WARNING] {issue}")
        for issue in audit.get("suggestions", []):
            click.echo(f"[AUDIT SUGGESTION] {issue}")

        sys.exit(1 if security.get("blocking") else 0)
    finally:
        os.chdir(original_dir)


commands = [install, validate, update, scan]
