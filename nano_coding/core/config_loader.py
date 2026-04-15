"""Configuration loading utilities."""

from __future__ import annotations

import json
from pathlib import Path

import click
import yaml

from nano_coding.core.project_discovery import find_nearest_agent_dir

USER_CONFIG_DIR = Path.home() / ".nano-coding-agent"
USER_CONFIG_PATH = USER_CONFIG_DIR / "config.yaml"


def _load_config_file(path: Path) -> dict:
    if not path.exists():
        return {}
    suffix = path.suffix.lower()
    try:
        with open(path, encoding="utf-8") as f:
            if suffix in (".yaml", ".yml"):
                data = yaml.safe_load(f)
            else:
                data = json.load(f)
    except (yaml.YAMLError, json.JSONDecodeError, OSError) as exc:
        click.echo(f"Warning: failed to load config from {path}: {exc}", err=True)
        return {}
    if not isinstance(data, dict):
        click.echo(f"Warning: config at {path} is not an object", err=True)
        return {}
    return data


def load_config(path: Path) -> dict:
    return _load_config_file(path)


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
        yaml_path = agent_dir / "config.yaml"
        json_path = agent_dir / "config.json"
        project_config = _load_config_file(yaml_path)
        if not project_config and yaml_path.exists():
            click.echo(
                f"[HINT] {yaml_path} exists but could not be parsed. "
                "This may be caused by an incompatible format from an older CLI version. "
                "Consider backing up your configuration and re-running 'nano-coding install .' "
                "to regenerate it.",
                err=True,
            )
        if not project_config:
            project_config = _load_config_file(json_path)
        config = merge_configs(config, project_config)

    return config
