"""Configuration loading utilities."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from nano_coding.core.project_discovery import find_nearest_agent_dir

USER_CONFIG_DIR = Path.home() / ".nano-coding-agent"
USER_CONFIG_PATH = USER_CONFIG_DIR / "config.json"


def load_config(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        print(f"Warning: failed to load config from {path}: {exc}", file=sys.stderr)
        return {}
    if not isinstance(data, dict):
        print(f"Warning: config at {path} is not a JSON object", file=sys.stderr)
        return {}
    return data


def get_default_config() -> dict:
    return {}


def merge_configs(base: dict, override: dict) -> dict:
    merged: dict = dict(base)
    for key, value in override.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = merge_configs(merged[key], value)
        elif (
            key in merged and isinstance(merged[key], list) and isinstance(value, list)
        ):
            try:
                merged[key] = list(dict.fromkeys(merged[key] + value))
            except TypeError:
                merged[key] = merged[key] + [
                    item for item in value if item not in merged[key]
                ]
        else:
            merged[key] = value
    return merged


def resolve_config(start_dir: Path | None = None) -> dict:
    config = get_default_config()
    config = merge_configs(config, load_config(USER_CONFIG_PATH))

    if start_dir is None:
        start_dir = Path.cwd()
    agent_dir = find_nearest_agent_dir(start_dir)
    if agent_dir is not None:
        project_config_path = agent_dir / "config.json"
        config = merge_configs(config, load_config(project_config_path))

    return config
