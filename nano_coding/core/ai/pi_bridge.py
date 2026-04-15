from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path

from nano_coding.core.ai.config import AiConfig
from nano_coding.core.project_discovery import find_nearest_agent_dir

# T6/T8 并行实现，若尚未完成则使用 mock fallback
try:
    from nano_coding.core.ai import prompts
except Exception:  # pragma: no cover
    prompts = None  # type: ignore[assignment]

try:
    from nano_coding.core.ai import review_types
except Exception:  # pragma: no cover
    review_types = None  # type: ignore[assignment]

try:
    from nano_coding.core.ai.review_types import ReviewResult
except Exception:  # pragma: no cover
    ReviewResult = dict  # type: ignore[misc]


class PiRuntimeNotInstalledError(RuntimeError):
    pass


class PiRuntimeError(RuntimeError):
    pass


class PiBridge:
    def __init__(self, agent_dir: Path | None = None) -> None:
        if agent_dir is None:
            nearest = find_nearest_agent_dir(Path.cwd())
            if nearest is None:
                raise PiRuntimeNotInstalledError(
                    "No .nano-coding-agent directory found. Run 'nano-coding install' first."
                )
            agent_dir = nearest
        self.pi_dir: Path = agent_dir / "pi"

    def _ensure_runtime(self) -> None:
        lock_file = self.pi_dir / "node_modules" / ".package-lock.json"
        pi_pkg = (
            self.pi_dir
            / "node_modules"
            / "@mariozechner"
            / "pi-coding-agent"
            / "package.json"
        )
        if not lock_file.exists() and not pi_pkg.exists():
            raise PiRuntimeNotInstalledError(
                "Pi runtime not installed. Run 'nano-coding install' first."
            )

    def _build_cmd(self, config: dict, prompt_file: Path) -> list[str]:
        tsx_cmd: list[str] = [
            "npx",
            "--prefix",
            str(self.pi_dir),
            "tsx",
            str(self.pi_dir / "pi_runner.ts"),
        ]
        node_cmd: list[str] = [
            "node",
            "--experimental-specifier-resolution=node",
            str(self.pi_dir / "pi_runner.ts"),
        ]
        tsx_bin = self.pi_dir / "node_modules" / ".bin" / "tsx"
        cmd = tsx_cmd if tsx_bin.exists() else node_cmd
        return cmd + [
            "--config",
            json.dumps(config),
            "--prompt-file",
            str(prompt_file),
        ]

    def run(self, config: dict, prompt: str, timeout: float = 120.0) -> dict:
        self._ensure_runtime()
        tmp_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".txt", delete=False, encoding="utf-8"
            ) as f:
                f.write(prompt)
                tmp_path = Path(f.name)
            cmd = self._build_cmd(config, tmp_path)
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=timeout
            )
            lines = [line for line in result.stdout.splitlines() if line.strip()]
            raw = lines[-1] if lines else result.stdout
            parsed = json.loads(raw)
        finally:
            if tmp_path is not None:
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass
        if not parsed.get("success"):
            raise PiRuntimeError(parsed.get("error", "Unknown error"))
        return parsed


def _mock_build_agents_md_review(content: str) -> str:
    return f"Review AGENTS.md:\n{content}"


def _mock_build_background_md_review(content: str) -> str:
    return f"Review BACKGROUND.md:\n{content}"


def _mock_build_agents_abort_review(content: str) -> str:
    return f"Review banned behaviors:\n{content}"


def _mock_build_subdir_agents_review(items: list[tuple[str, str]]) -> str:
    lines = ["Review subdirectory AGENTS.md files:"]
    for path, content in items:
        lines.append(f"--- {path} ---")
        lines.append(content)
    return "\n".join(lines)


def _mock_parse_llm_response(review_type: str, response: str) -> dict:
    return {"review_type": review_type, "response": response}


def run_llm_review(
    cwd: Path, review_type: str, context: dict, config: AiConfig
) -> ReviewResult:
    if not config.api_key:
        raise PiRuntimeError(
            "No API key configured. Set ANTHROPIC_API_KEY or OPENAI_API_KEY "
            "environment variable, or add api_key to .nano-coding-agent/config.yaml"
        )

    bridge = PiBridge()
    runner_config = {
        "provider": config.provider,
        "model": config.model,
        "api_key": config.api_key,
        "thinking_level": config.thinking_level,
        "cwd": str(cwd.resolve()),
    }

    if review_type == "agents-md":
        content = (cwd / "AGENTS.md").read_text(encoding="utf-8")
        if prompts is not None:
            prompt = prompts.build_agents_md_review(content)
        else:
            prompt = _mock_build_agents_md_review(content)
    elif review_type == "background-md":
        content = (cwd / "BACKGROUND.md").read_text(encoding="utf-8")
        if prompts is not None:
            prompt = prompts.build_background_md_review(content)
        else:
            prompt = _mock_build_background_md_review(content)
    elif review_type == "agents-abort":
        abort_file = cwd / "AGENTS_ABORT.md"
        if not abort_file.exists():
            abort_file = cwd / "BANNED-AGENT-BEHAVIORS.md"
        content = abort_file.read_text(encoding="utf-8") if abort_file.exists() else ""
        if prompts is not None:
            prompt = prompts.build_agents_abort_review(content)
        else:
            prompt = _mock_build_agents_abort_review(content)
    elif review_type == "subdir-agents":
        items: list[tuple[str, str]] = []
        for p in cwd.rglob("AGENTS.md"):
            rel = p.relative_to(cwd)
            parts = rel.parts
            if len(parts) <= 1:
                continue
            if any(
                part.startswith(".") or part == "node_modules" or part == "__pycache__"
                for part in parts[:-1]
            ):
                continue
            items.append((str(rel), p.read_text(encoding="utf-8")))
        if prompts is not None:
            prompt = prompts.build_subdir_agents_review(items)
        else:
            prompt = _mock_build_subdir_agents_review(items)
    else:
        raise PiRuntimeError(f"Unknown review type: {review_type}")

    result = bridge.run(runner_config, prompt)
    if review_types is not None:
        return review_types.parse_llm_response(review_type, result["response"])
    return _mock_parse_llm_response(review_type, result["response"])
