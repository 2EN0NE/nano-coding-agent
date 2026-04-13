import os
import sys
from pathlib import Path

import click

from nano_coding.core.installer import install_hooks_and_principles
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
from nano_coding.core.validator import validate_project


@click.group()
def cli() -> None:
    """项目治理相关命令"""
    pass


@register_practice(
    principle='行为边界与"防呆"原则 (Guardrails & Boundaries)',
    practices={"禁止操作": ["guard", "install"]},
)
@cli.command()
@click.argument("target_dir")
def install(target_dir: str) -> None:
    """将pre-commit钩子和基础principles/目录安装到Git仓库中。

    Examples:

        $ nano-coding guard install .
    """
    install_hooks_and_principles(target_dir)


@register_practice(
    principle='行为边界与"防呆"原则 (Guardrails & Boundaries)',
    practices={"禁止操作": ["guard", "validate"]},
)
@register_practice(
    principle="测试先行原则（TDD First）",
    practices={"区分测试类型": ["guard", "validate"]},
)
@cli.command()
@click.argument("target_dir")
def validate(target_dir: str) -> None:
    """验证项目是否满足基础治理规则。

    Examples:

        $ nano-coding guard validate .
    """
    result = validate_project(target_dir)
    for issue in result.get("blocking", []):
        click.echo(f"[BLOCKING] {issue}")
    for issue in result.get("warnings", []):
        click.echo(f"[WARNING] {issue}")
    sys.exit(0 if result["success"] else 1)


@register_practice(
    principle="最重要原则：核心指导原则需要由人类审核",
    practices={"共性个性区分": ["guard", "merge"]},
)
@cli.command()
@click.option("--principles", required=True, help="Path to principles markdown file")
@click.option("--target", required=True, help="Path to target AGENTS.md")
def merge(principles: str, target: str) -> None:
    """将源markdown文件中的原则块合并到现有的AGENTS.md中，通过语义相似度去重。

    Examples:

        $ nano-coding guard merge --principles principles/core.md --target AGENTS.md
    """
    principles_file = Path(principles)
    target_file = Path(target)

    if not principles_file.exists():
        click.echo(f"[ERROR] Principles file not found: {principles}")
        sys.exit(1)
    if not target_file.exists():
        click.echo(f"[ERROR] Target file not found: {target}")
        sys.exit(1)

    principles_content = principles_file.read_text(encoding="utf-8")
    target_content = target_file.read_text(encoding="utf-8")

    incoming_blocks = extractPrincipleBlocks(principles_content)
    target_dir = target_file.parent
    incoming_blocks = resolve_principle_tags(
        incoming_blocks,
        str(target_dir) if target_dir.exists() else None,
    )
    merged = mergePrinciplesIntoDocument(target_content, incoming_blocks)

    target_file.write_text(merged, encoding="utf-8")
    click.echo(f"Merged {len(incoming_blocks)} principle blocks into {target}")


@register_practice(
    principle='行为边界与"防呆"原则 (Guardrails & Boundaries)',
    practices={"安全防线": ["guard", "scan"]},
)
@cli.command()
@click.option(
    "--path", default=".", help="Directory to scan (default: current directory)"
)
@click.option("--level", default="standard", help="Audit level (default: standard)")
def scan(path: str, level: str) -> None:
    """对项目运行安全和审计扫描。报告阻塞性问题、警告和建议。

    Examples:

        $ nano-coding guard scan --path .
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
