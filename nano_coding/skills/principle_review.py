import subprocess
import sys
from pathlib import Path

import click
import yaml

from nano_coding.core.principles import (
    NANO_CODING_END,
    NANO_CODING_START,
)
from nano_coding.core.registry import register_practice


@click.group(name="principle-review", invoke_without_command=True)
@click.argument("target_dir", default=".")
@click.option("--check-changes", is_flag=True)
@click.option("--separate-concerns", is_flag=True)
@click.option("--length-limit", is_flag=True)
@click.pass_context
@register_practice(
    principle="最重要原则：核心指导原则需要由人类审核",
    practices={
        "变更确认": ["principle-review"],
        "控制长度": ["principle-review"],
    },
)
def cli(ctx, target_dir, check_changes, separate_concerns, length_limit):
    """审查目标项目的核心指导原则合规性。

    Examples:

        $ uv run nano-coding principle-review .
        $ uv run nano-coding principle-review . --check-changes
    """
    if ctx.invoked_subcommand is not None:
        return

    if not any([check_changes, separate_concerns, length_limit]):
        check_changes = True
        separate_concerns = True
        length_limit = True

    target_path = Path(target_dir)
    has_failure = False

    if check_changes:
        if not _run_check_changes(target_path):
            has_failure = True

    if separate_concerns:
        if not _run_separate_concerns(target_path):
            has_failure = True

    if length_limit:
        _run_length_limit(target_path)

    sys.exit(1 if has_failure else 0)


def _run_check_changes(target_path: Path) -> bool:
    if not (target_path / ".git").exists():
        click.echo(f"[ERROR] Not a git repository: {target_path}")
        return False

    changed = set()
    for cmd_args in [
        ["git", "-C", str(target_path), "diff", "--name-only", "HEAD"],
        ["git", "-C", str(target_path), "diff", "--cached", "--name-only"],
    ]:
        result = subprocess.run(cmd_args, capture_output=True, text=True)
        if result.returncode == 0 and result.stdout:
            for line in result.stdout.strip().splitlines():
                if line:
                    changed.add(line)

    agent_dir = target_path / ".nano-coding-agent"
    if agent_dir.exists():
        monitored = [
            "AGENTS.md",
            "README.md",
            "BANNED-AGENT-BEHAVIORS",
            "BACKGROUND.md",
            ".nano-coding-agent/AGENTS.md",
            ".nano-coding-agent/principles/core.md",
            ".nano-coding-agent/config.json",
        ]
    else:
        monitored = [
            "AGENTS.md",
            "README.md",
            "BANNED-AGENT-BEHAVIORS",
            "BACKGROUND.md",
            "principles/core.md",
        ]

    config_file = target_path / ".nano-coding.yaml"
    if config_file.exists():
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            if data and isinstance(data.get("monitored_principle_files"), list):
                monitored.extend(data["monitored_principle_files"])
        except Exception:
            pass

    matches = []
    for p in changed:
        if p in monitored or Path(p).name in monitored:
            matches.append(p)
    if not matches:
        click.echo("[OK] No core principle document changes detected.")
        return True

    click.echo("[REVIEW REQUIRED]")
    for m in matches:
        click.echo(f"  - {m}")

    prompt_text = (
        "I have personally reviewed the revisions to the core principles document."
    )
    click.echo(prompt_text)

    if sys.stdin.isatty():
        try:
            answer = click.prompt(
                "Please type the confirmation statement above", type=str
            )
        except click.exceptions.Abort:
            sys.exit(1)
        if answer.strip() == prompt_text.strip():
            return True
        sys.exit(1)
    else:
        sys.exit(1)


def _run_separate_concerns(target_path: Path) -> bool:
    agents_md = target_path / "AGENTS.md"
    if not agents_md.exists():
        click.echo(f"[ERROR] AGENTS.md not found in {target_path}")
        return False

    content = agents_md.read_text(encoding="utf-8")
    start_idx = content.find(NANO_CODING_START)
    end_idx = content.find(NANO_CODING_END)

    if start_idx == -1 or end_idx == -1 or start_idx >= end_idx:
        click.echo(
            "[FAIL] AGENTS.md missing NANO_CODING_GENERATED markers or internal separators."
        )
        return False

    block = content[start_idx + len(NANO_CODING_START) : end_idx]
    if "---" not in block:
        click.echo(
            "[FAIL] AGENTS.md missing NANO_CODING_GENERATED markers or internal separators."
        )
        return False

    click.echo("[OK] AGENTS.md contains NANO_CODING_GENERATED markers and separators.")
    return True


def _run_length_limit(target_path: Path) -> None:
    files_to_check: list[Path] = []
    agents_md = target_path / "AGENTS.md"
    if agents_md.exists():
        files_to_check.append(agents_md)

    agent_principles_dir = target_path / ".nano-coding-agent" / "principles"
    legacy_principles_dir = target_path / "principles"
    if agent_principles_dir.exists() and agent_principles_dir.is_dir():
        files_to_check.extend(sorted(agent_principles_dir.rglob("*.md")))
    elif legacy_principles_dir.exists() and legacy_principles_dir.is_dir():
        files_to_check.extend(sorted(legacy_principles_dir.rglob("*.md")))

    warnings = []
    for file_path in files_to_check:
        lines = file_path.read_text(encoding="utf-8").splitlines()
        total_lines = len(lines)
        if total_lines > 1000:
            warnings.append(
                f"[WARNING] File {file_path.name} exceeds 1000 lines ({total_lines})."
            )

        principle_blocks = _split_principle_blocks(lines)
        for title, block_lines in principle_blocks:
            if len(block_lines) > 150:
                warnings.append(
                    f'[WARNING] Principle "{title}" in {file_path.name} exceeds 150 lines ({len(block_lines)}).'
                )

    if warnings:
        for w in warnings:
            click.echo(w)
    else:
        click.echo("[OK] All principle documents and blocks are within length limits.")


def _split_principle_blocks(lines: list[str]) -> list[tuple[str, list[str]]]:
    blocks: list[tuple[str, list[str]]] = []
    current_title = ""
    current_lines: list[str] = []

    for line in lines:
        if line.startswith("### "):
            if current_title:
                blocks.append((current_title, current_lines))
            current_title = line[4:].strip()
            current_lines = [line]
        elif current_title:
            current_lines.append(line)

    if current_title:
        blocks.append((current_title, current_lines))

    return blocks
