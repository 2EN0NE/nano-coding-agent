from __future__ import annotations

import json
from pathlib import Path

import click

from nano_coding.core.ai.config import load_ai_config
from nano_coding.core.ai.pi_bridge import PiRuntimeError, run_llm_review
from nano_coding.core.ai.review_types import ReviewResult, Severity
from nano_coding.core.project_discovery import find_nearest_agent_dir


def _print_text_report(results: list[ReviewResult], errors: list[str]) -> None:
    lines: list[str] = []
    lines.append("=" * 40)
    lines.append("AI Review Report")
    lines.append("=" * 40)

    for result in results:
        lines.append(f"\n## Review: {result.review_type}")
        lines.append(f"Summary: {result.summary}")
        for issue in result.issues:
            if issue.severity == Severity.BLOCKING:
                prefix = "[BLOCKING]"
            elif issue.severity == Severity.WARNING:
                prefix = "[WARNING]"
            else:
                prefix = "[SUGGESTION]"
            lines.append(f"{prefix} {issue.title}")
            lines.append(f"  Detail: {issue.detail}")
            lines.append(f"  Suggestion: {issue.suggestion}")

    if errors:
        lines.append("\n## Errors")
        for error in errors:
            lines.append(error)

    click.echo("\n".join(lines))


@click.command(name="ai-review")
@click.argument(
    "target_dir",
    default=".",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
)
@click.option(
    "--review-type",
    "review_type",
    type=click.Choice(
        ["agents-md", "background-md", "agents-abort", "subdir-agents", "all"]
    ),
    default="all",
    help="Type of review to perform (default: all)",
)
@click.option(
    "--json",
    "output_json",
    is_flag=True,
    help="Output structured JSON instead of text report",
)
@click.option("--model", help="Override the model selection from config")
def ai_review(
    target_dir: Path, review_type: str, output_json: bool, model: str | None
) -> None:
    """使用AI对项目原则文档进行审查。

    Examples:

        $ uv run nano-coding ai-review .
        $ uv run nano-coding ai-review . --review-type agents-md
        $ uv run nano-coding ai-review . --json
    """
    agent_dir = find_nearest_agent_dir(target_dir)
    if agent_dir is None:
        click.echo(
            "[ERROR] No .nano-coding-agent directory found. Run 'nano-coding install' first.",
            err=True,
        )
        raise click.Abort()

    config = load_ai_config(agent_dir)
    if model:
        config.model = model

    if not config.api_key:
        click.echo(
            "[ERROR] No API key configured. Set KIMI_API_KEY, ANTHROPIC_API_KEY or OPENAI_API_KEY "
            "environment variable, or add api_key to .nano-coding-agent/config.yaml",
            err=True,
        )
        raise click.Abort()

    review_types_to_run = (
        config.enabled_reviews if review_type == "all" else [review_type]
    )

    results: list[ReviewResult] = []
    errors: list[str] = []
    for rt in review_types_to_run:
        try:
            result = run_llm_review(target_dir, rt, {}, config)
            results.append(result)
        except FileNotFoundError as e:
            filename = getattr(e, "filename", "unknown")
            errors.append(f"[{rt}] Required file not found: {filename}")
        except PiRuntimeError as e:
            errors.append(f"[{rt}] {e}")
        except Exception as e:
            errors.append(f"[{rt}] Unexpected error: {e}")

    if output_json:
        output = []
        for r in results:
            output.append(
                {
                    "review_type": r.review_type,
                    "summary": r.summary,
                    "issues": [
                        {
                            "severity": issue.severity.value,
                            "title": issue.title,
                            "detail": issue.detail,
                            "suggestion": issue.suggestion,
                        }
                        for issue in r.issues
                    ],
                }
            )
        if errors:
            output.append({"errors": errors})
        click.echo(json.dumps(output, indent=2, ensure_ascii=False))
    else:
        _print_text_report(results, errors)

    has_blocking = any(
        any(issue.severity == Severity.BLOCKING for issue in r.issues) for r in results
    )
    if errors or has_blocking:
        raise click.Abort()
