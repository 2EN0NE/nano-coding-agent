import json
import sys
from pathlib import Path

import pytest

from nano_coding.core.ai.config import AiConfig
from nano_coding.core.ai.pi_bridge import (
    PiBridge,
    PiRuntimeError,
    PiRuntimeNotInstalledError,
    run_llm_review,
)
from nano_coding.core.ai.review_types import ReviewResult


class TestPiBridge:
    def test_ensure_runtime_missing_node_modules(self, tmp_path: Path) -> None:
        agent_dir = tmp_path / ".nano-coding-agent"
        agent_dir.mkdir()
        bridge = PiBridge(agent_dir=agent_dir)
        with pytest.raises(PiRuntimeNotInstalledError):
            bridge._ensure_runtime()

    def test_ensure_runtime_present_lock_file(self, tmp_path: Path) -> None:
        agent_dir = tmp_path / ".nano-coding-agent"
        pi_dir = agent_dir / "pi"
        node_modules = pi_dir / "node_modules"
        node_modules.mkdir(parents=True)
        (node_modules / ".package-lock.json").write_text("{}")
        bridge = PiBridge(agent_dir=agent_dir)
        bridge._ensure_runtime()

    def test_ensure_runtime_present_pi_pkg(self, tmp_path: Path) -> None:
        agent_dir = tmp_path / ".nano-coding-agent"
        pi_dir = agent_dir / "pi"
        pkg = (
            pi_dir
            / "node_modules"
            / "@mariozechner"
            / "pi-coding-agent"
            / "package.json"
        )
        pkg.parent.mkdir(parents=True)
        pkg.write_text("{}")
        bridge = PiBridge(agent_dir=agent_dir)
        bridge._ensure_runtime()

    def test_build_cmd_with_tsx(self, tmp_path: Path) -> None:
        agent_dir = tmp_path / ".nano-coding-agent"
        pi_dir = agent_dir / "pi"
        tsx_bin = pi_dir / "node_modules" / ".bin" / "tsx"
        tsx_bin.parent.mkdir(parents=True)
        tsx_bin.write_text("#!/bin/sh\necho tsx")
        runner = pi_dir / "pi_runner.ts"
        runner.write_text("console.log('hello')")
        bridge = PiBridge(agent_dir=agent_dir)
        config = {"provider": "anthropic"}
        prompt_file = tmp_path / "prompt.txt"
        cmd = bridge._build_cmd(config, prompt_file)
        assert cmd[0] == "npx"
        assert "--prefix" in cmd
        assert "tsx" in cmd
        assert "--config" in cmd
        assert "--prompt-file" in cmd
        assert str(prompt_file) in cmd

    def test_build_cmd_without_tsx(self, tmp_path: Path) -> None:
        agent_dir = tmp_path / ".nano-coding-agent"
        pi_dir = agent_dir / "pi"
        runner = pi_dir / "pi_runner.ts"
        runner.parent.mkdir(parents=True, exist_ok=True)
        runner.write_text("console.log('hello')")
        bridge = PiBridge(agent_dir=agent_dir)
        config = {"provider": "anthropic"}
        prompt_file = tmp_path / "prompt.txt"
        cmd = bridge._build_cmd(config, prompt_file)
        assert cmd[0] == "node"
        assert "--experimental-specifier-resolution=node" in cmd
        assert str(runner) in cmd
        assert "--config" in cmd
        assert "--prompt-file" in cmd
        assert str(prompt_file) in cmd

    def test_run_success_with_fake_runner(self, tmp_path: Path, monkeypatch) -> None:
        agent_dir = tmp_path / ".nano-coding-agent"
        pi_dir = agent_dir / "pi"
        node_modules = pi_dir / "node_modules"
        node_modules.mkdir(parents=True)
        (node_modules / ".package-lock.json").write_text("{}")
        runner = pi_dir / "pi_runner.ts"
        runner.write_text("pass")
        bridge = PiBridge(agent_dir=agent_dir)

        fake_output = json.dumps({"success": True, "response": "hello"})
        monkeypatch.setattr(
            bridge,
            "_build_cmd",
            lambda _config, _prompt: [sys.executable, "-c", f"print({fake_output!r})"],
        )
        result = bridge.run({"provider": "anthropic"}, "test prompt")
        assert result["success"] is True
        assert result["response"] == "hello"

    def test_run_failure_with_fake_runner(self, tmp_path: Path, monkeypatch) -> None:
        agent_dir = tmp_path / ".nano-coding-agent"
        pi_dir = agent_dir / "pi"
        node_modules = pi_dir / "node_modules"
        node_modules.mkdir(parents=True)
        (node_modules / ".package-lock.json").write_text("{}")
        runner = pi_dir / "pi_runner.ts"
        runner.write_text("pass")
        bridge = PiBridge(agent_dir=agent_dir)

        fake_output = json.dumps({"success": False, "error": "boom"})
        monkeypatch.setattr(
            bridge,
            "_build_cmd",
            lambda _config, _prompt: [sys.executable, "-c", f"print({fake_output!r})"],
        )
        with pytest.raises(PiRuntimeError, match="boom"):
            bridge.run({"provider": "anthropic"}, "test prompt")

    def test_run_parses_last_non_empty_line(self, tmp_path: Path, monkeypatch) -> None:
        agent_dir = tmp_path / ".nano-coding-agent"
        pi_dir = agent_dir / "pi"
        node_modules = pi_dir / "node_modules"
        node_modules.mkdir(parents=True)
        (node_modules / ".package-lock.json").write_text("{}")
        runner = pi_dir / "pi_runner.ts"
        runner.write_text("pass")
        bridge = PiBridge(agent_dir=agent_dir)

        fake_output = json.dumps({"success": True, "response": "ok"})
        code = f"print('some log')\nprint()\nprint({fake_output!r})"
        monkeypatch.setattr(
            bridge, "_build_cmd", lambda _config, _prompt: [sys.executable, "-c", code]
        )
        result = bridge.run({"provider": "anthropic"}, "test prompt")
        assert result["response"] == "ok"


class TestRunLlmReview:
    def test_missing_api_key(self, tmp_path: Path) -> None:
        config = AiConfig(provider="anthropic", model="claude", api_key=None)
        with pytest.raises(PiRuntimeError, match="No API key configured"):
            run_llm_review(tmp_path, "agents-md", {}, config)

    def test_agents_md_review(self, tmp_path: Path, monkeypatch) -> None:
        (tmp_path / "AGENTS.md").write_text("# Agents")
        config = AiConfig(provider="anthropic", model="claude", api_key="secret")

        def fake_run(_self, _config, prompt):
            assert "AGENTS.md" in prompt
            return {"success": True, "response": '{"summary": "good", "issues": []}'}

        monkeypatch.setattr(PiBridge, "run", fake_run)
        result = run_llm_review(tmp_path, "agents-md", {}, config)
        assert isinstance(result, ReviewResult)
        assert result.review_type == "agents-md"
        assert result.summary == "good"

    def test_background_md_review(self, tmp_path: Path, monkeypatch) -> None:
        (tmp_path / "BACKGROUND.md").write_text("# Background")
        config = AiConfig(provider="anthropic", model="claude", api_key="secret")

        def fake_run(_self, _config, prompt):
            assert "BACKGROUND.md" in prompt
            return {"success": True, "response": '{"summary": "good", "issues": []}'}

        monkeypatch.setattr(PiBridge, "run", fake_run)
        result = run_llm_review(tmp_path, "background-md", {}, config)
        assert result.review_type == "background-md"
        assert result.summary == "good"

    def test_agents_abort_review_agents_abort_md(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        (tmp_path / "AGENTS_ABORT.md").write_text("# Abort")
        config = AiConfig(provider="anthropic", model="claude", api_key="secret")

        def fake_run(_self, _config, prompt):
            assert "banned-agent-behaviors" in prompt
            return {"success": True, "response": '{"summary": "good", "issues": []}'}

        monkeypatch.setattr(PiBridge, "run", fake_run)
        result = run_llm_review(tmp_path, "agents-abort", {}, config)
        assert result.review_type == "agents-abort"
        assert result.summary == "good"

    def test_agents_abort_review_fallback_banned(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        (tmp_path / "BANNED-AGENT-BEHAVIORS.md").write_text("# Banned")
        config = AiConfig(provider="anthropic", model="claude", api_key="secret")

        def fake_run(_self, _config, prompt):
            assert "banned-agent-behaviors" in prompt
            return {"success": True, "response": '{"summary": "good", "issues": []}'}

        monkeypatch.setattr(PiBridge, "run", fake_run)
        result = run_llm_review(tmp_path, "agents-abort", {}, config)
        assert result.review_type == "agents-abort"
        assert result.summary == "good"

    def test_subdir_agents_review(self, tmp_path: Path, monkeypatch) -> None:
        sub = tmp_path / "src" / "core"
        sub.mkdir(parents=True)
        (sub / "AGENTS.md").write_text("# Sub")
        config = AiConfig(provider="anthropic", model="claude", api_key="secret")

        def fake_run(_self, _config, prompt):
            assert "src/core/AGENTS.md" in prompt
            return {"success": True, "response": '{"summary": "good", "issues": []}'}

        monkeypatch.setattr(PiBridge, "run", fake_run)
        result = run_llm_review(tmp_path, "subdir-agents", {}, config)
        assert result.review_type == "subdir-agents"
        assert result.summary == "good"

    def test_unknown_review_type(self, tmp_path: Path) -> None:
        config = AiConfig(provider="anthropic", model="claude", api_key="secret")
        with pytest.raises(PiRuntimeError, match="Unknown review type"):
            run_llm_review(tmp_path, "unknown", {}, config)
