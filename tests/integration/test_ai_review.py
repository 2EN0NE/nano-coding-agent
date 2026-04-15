"""Integration tests for ai-review command using mock pi runtime.

TESTED_COMMANDS declaration for coverage tracking:
- ("ai-review",)
"""

import json
import subprocess
from pathlib import Path

import yaml
from click.testing import CliRunner

from nano_coding.skills.ai_review import ai_review

TESTED_COMMANDS = [
    ("ai-review",),
]

# Mock pi_runner.ts written as CommonJS so Node can execute it directly.
MOCK_PI_RUNNER = """const { readFileSync } = require("node:fs");
const promptIdx = process.argv.indexOf("--prompt-file");
const promptFile = process.argv[promptIdx + 1];
const prompt = readFileSync(promptFile, "utf-8");
const response = "Mock review for prompt length " + prompt.length;
const jsonResponse = JSON.stringify({
  summary: response,
  issues: [
    {
      severity: "suggestion",
      title: "Mock issue",
      detail: "This is a mock response.",
      suggestion: "No action needed."
    }
  ]
});
const output = JSON.stringify({
  success: true,
  response: "```json\\n" + jsonResponse + "\\n```"
});
process.stdout.write(output + "\\n");
"""


def _setup_mock_project(
    root: Path,
    with_agents_md: bool = True,
    with_background_md: bool = True,
    with_banned_md: bool = True,
    with_pi_runtime: bool = True,
    api_key: str | None = "test-key",
) -> None:
    subprocess.run(["git", "init", str(root)], check=True, capture_output=True)

    agent_dir = root / ".nano-coding-agent"
    agent_dir.mkdir()

    config: dict = {"ai": {}}
    if api_key is not None:
        config["ai"]["api_key"] = api_key
    config["ai"]["provider"] = "anthropic"
    config["ai"]["model"] = "claude-3-5-sonnet"
    config["ai"]["thinking_level"] = "low"

    (agent_dir / "config.yaml").write_text(yaml.dump(config), encoding="utf-8")

    if with_agents_md:
        (root / "AGENTS.md").write_text(
            "# Test Project\n\n## 基础原则\n- Test rule\n", encoding="utf-8"
        )
    if with_background_md:
        (root / "BACKGROUND.md").write_text(
            "# Background\n\nProject vision.\n", encoding="utf-8"
        )
    if with_banned_md:
        (root / "BANNED-AGENT-BEHAVIORS.md").write_text(
            "# Banned\n\nNo bad actions.\n", encoding="utf-8"
        )

    if with_pi_runtime:
        pi_dir = agent_dir / "pi"
        pi_dir.mkdir()
        (pi_dir / "package.json").write_text('{"name": "mock-pi"}', encoding="utf-8")
        node_modules = pi_dir / "node_modules"
        node_modules.mkdir()
        (node_modules / ".package-lock.json").write_text("{}", encoding="utf-8")
        (pi_dir / "pi_runner.ts").write_text(MOCK_PI_RUNNER, encoding="utf-8")


class TestAiReviewIntegration:
    def test_full_install_ai_review_flow(self, tmp_path: Path, monkeypatch) -> None:
        _setup_mock_project(tmp_path)
        monkeypatch.chdir(str(tmp_path))
        runner = CliRunner()
        result = runner.invoke(ai_review, [str(tmp_path)])

        assert result.exit_code == 0, result.output
        assert "Mock review" in result.output
        assert "[SUGGESTION] Mock issue" in result.output

    def test_ai_review_json_output(self, tmp_path: Path, monkeypatch) -> None:
        _setup_mock_project(tmp_path)
        monkeypatch.chdir(str(tmp_path))
        runner = CliRunner()
        result = runner.invoke(ai_review, [str(tmp_path), "--json"])

        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert isinstance(data, list)
        assert len(data) > 0
        for item in data:
            assert "review_type" in item
            assert "summary" in item
            assert "issues" in item
            assert isinstance(item["issues"], list)

    def test_missing_pi_runtime_error(self, tmp_path: Path, monkeypatch) -> None:
        _setup_mock_project(tmp_path, with_pi_runtime=False)
        monkeypatch.chdir(str(tmp_path))
        runner = CliRunner()
        result = runner.invoke(ai_review, [str(tmp_path)])

        assert result.exit_code != 0
        assert (
            "Pi runtime not installed" in result.output
            or "No .nano-coding-agent directory found" in result.output
        )

    def test_missing_api_key_error(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("KIMI_API_KEY", raising=False)
        _setup_mock_project(tmp_path, api_key=None)
        monkeypatch.chdir(str(tmp_path))
        runner = CliRunner()
        result = runner.invoke(ai_review, [str(tmp_path)])

        assert result.exit_code != 0
        assert "No API key configured" in result.output

    def test_missing_agents_md_error(self, tmp_path: Path, monkeypatch) -> None:
        _setup_mock_project(tmp_path, with_agents_md=False)
        monkeypatch.chdir(str(tmp_path))
        runner = CliRunner()
        result = runner.invoke(
            ai_review,
            [str(tmp_path), "--review-type", "agents-md"],
        )

        assert result.exit_code != 0
        assert "Required file not found" in result.output or "Errors" in result.output
