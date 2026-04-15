from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class AiConfig:
    provider: str = "kimi-coding"
    model: str = "k2p5"
    api_key: str | None = None
    thinking_level: str = "low"
    enabled_reviews: list[str] = field(
        default_factory=lambda: [
            "agents-md",
            "background-md",
            "agents-abort",
            "subdir-agents",
        ]
    )


def load_ai_config(agent_dir: Path) -> AiConfig:
    config_file = agent_dir / "config.yaml"
    legacy_file = agent_dir / "config.json"
    raw: dict[str, Any] = {}
    if config_file.exists():
        try:
            raw = yaml.safe_load(config_file.read_text(encoding="utf-8")) or {}
        except Exception:
            raw = {}
    elif legacy_file.exists():
        try:
            import json

            raw = json.loads(legacy_file.read_text(encoding="utf-8"))
        except Exception:
            raw = {}
    ai_raw = raw.get("ai", {}) if isinstance(raw, dict) else {}
    provider = ai_raw.get("provider", "kimi-coding")
    model = ai_raw.get("model", "k2p5")
    thinking_level = ai_raw.get("thinking_level", "low")
    enabled_reviews = ai_raw.get(
        "enabled_reviews",
        ["agents-md", "background-md", "agents-abort", "subdir-agents"],
    )

    api_key = (
        os.environ.get("KIMI_API_KEY")
        or os.environ.get("ANTHROPIC_API_KEY")
        or os.environ.get("OPENAI_API_KEY")
        or ai_raw.get("api_key")
    )
    if provider.lower() == "openai":
        api_key = os.environ.get("OPENAI_API_KEY") or api_key
    elif provider.lower() == "anthropic":
        api_key = os.environ.get("ANTHROPIC_API_KEY") or api_key
    elif provider.lower() == "kimi-coding":
        api_key = os.environ.get("KIMI_API_KEY") or api_key

    return AiConfig(
        provider=provider,
        model=model,
        api_key=api_key,
        thinking_level=thinking_level,
        enabled_reviews=enabled_reviews,
    )
